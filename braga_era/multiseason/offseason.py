"""Opt-in, NONCANONICAL forward labour/economic model; no production authority.

Every assumed balance, wage, age and revenue is explicit proposed data. Native
history is never backfilled. Signed store operations make decisions transactional
and exact retries replay the original negotiation rather than choosing a seed.
"""
from collections import Counter,defaultdict
from datetime import date,timedelta
import json
import random
from ..history import canonical_json as encode,digest
from .competitions import required,club
from . import market

POLICY='autonomous-offseason-development-1'
DDL="""
CREATE TABLE ms_offseasons(season INTEGER PRIMARY KEY,policy TEXT NOT NULL,dated TEXT NOT NULL,state TEXT NOT NULL,summary_json TEXT);
CREATE TABLE ms_economics(club TEXT NOT NULL,season INTEGER NOT NULL,scenario_json TEXT NOT NULL,PRIMARY KEY(club,season));
CREATE TABLE ms_lifecycle(player INTEGER PRIMARY KEY,age INTEGER NOT NULL,observed_season INTEGER NOT NULL,status TEXT NOT NULL,provenance_json TEXT NOT NULL);
CREATE TABLE ms_market_decisions(id TEXT PRIMARY KEY,season INTEGER NOT NULL,club TEXT,player INTEGER,kind TEXT NOT NULL,detail_json TEXT NOT NULL);
CREATE TABLE ms_obligations(id TEXT PRIMARY KEY,club TEXT NOT NULL,payee TEXT,due TEXT NOT NULL,amount_cents INTEGER NOT NULL,direction INTEGER NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,detail_json TEXT NOT NULL);
CREATE INDEX ms_due_obligations ON ms_obligations(status,due);
CREATE TABLE ms_registrations(season INTEGER NOT NULL,player INTEGER NOT NULL,club TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(season,player));
CREATE INDEX ms_offseason_contract_club ON ms_contracts(club,status);
"""
TABLES=frozenset({'ms_offseasons','ms_economics','ms_lifecycle','ms_market_decisions','ms_obligations','ms_registrations'})
TARGETS={'GK':3,'DF':8,'MF':7,'FW':5}


def installed(c):return c.execute("SELECT 1 FROM sqlite_master WHERE name='ms_offseasons' AND type='table'").fetchone() is not None


def install(c,a):
    required(a,'policy')
    if a['policy']!=POLICY or installed(c):raise ValueError('Unsupported or already installed offseason migration')
    if c.execute("SELECT test_only FROM ms_meta").fetchone()[0]!=1:raise ValueError('Offseason is TEST-only')
    for sql in DDL.split(';'):
        if sql.strip():c.execute(sql)
    parent=c.execute('SELECT parent_sha256 FROM ms_meta').fetchone()[0]
    c.execute('INSERT INTO ms_migrations VALUES(2,?,?)',(digest(DDL),parent))
    return {'migration':2,'ddl_sha256':digest(DDL),'policy':POLICY,'acceptance_eligible':False}


def rng(c,*stream):
    seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
    return random.Random(int(digest({'seed':seed,'stream':stream,'policy':POLICY}),16))


def note(c,year,key,pid,kind,detail):
    identity=digest({'year':year,'club':key,'player':pid,'kind':kind,'detail':detail})
    c.execute('INSERT INTO ms_market_decisions VALUES(?,?,?,?,?,?)',(identity,year,key,pid,kind,encode(detail)))
    return identity


def state(c,pid):return json.loads(c.execute('SELECT state_json FROM world_player_state WHERE player_id=?',(pid,)).fetchone()[0])
def save_state(c,pid,value):c.execute('UPDATE world_player_state SET state_json=? WHERE player_id=?',(encode(value),pid))


def wage(attrs):return max(80000,int((attrs['ovr']-40)**2*3500)) # cents/month, explicit forward assumption


def active_wages(c,key,dated):
    own=c.execute("SELECT coalesce(sum(wage_cents),0) FROM ms_contracts t WHERE club=? AND status='active' AND starts<=? AND ends>=? AND NOT EXISTS(SELECT 1 FROM ms_loans l WHERE l.player=t.player AND l.starts<=? AND l.ends>=? AND l.wage_share_bps=10000)",(key,dated,dated,dated,dated)).fetchone()[0]
    borrowed=c.execute("SELECT coalesce(sum(t.wage_cents),0) FROM ms_loans l JOIN ms_contracts t ON t.player=l.player WHERE l.borrower=? AND l.starts<=? AND l.ends>=? AND t.status='active' AND l.wage_share_bps=10000",(key,dated,dated)).fetchone()[0]
    return own+borrowed


def budget(c,key,year):
    row=c.execute('SELECT scenario_json FROM ms_economics WHERE club=? AND season=?',(key,year)).fetchone()
    if not row:raise ValueError('Missing explicit club economic scenario')
    return json.loads(row[0])


def payable(c,key):return c.execute("SELECT coalesce(sum(amount_cents),0) FROM ms_obligations WHERE club=? AND direction=-1 AND status='pending' AND kind IN ('installment','agent','signing_bonus','performance_bonus')",(key,)).fetchone()[0]


def affordable(c,key,year,dated,fee,new_wage,extras=0,replace_wage=0):
    acc=market.account(c,key);s=budget(c,key,year)
    annual=12*(active_wages(c,key,dated)+new_wage-replace_wage)
    return (fee<=acc['fee_authority_cents'] and new_wage*12<=acc['wage_authority_cents']
        and annual<=s['annual_wage_cap_cents']
        and acc['cash_cents']-acc['reserve_cents']-payable(c,key)>=fee+extras+2*(annual//12))


def obligation(c,identity,key,payee,due,amount,direction,kind,detail):
    c.execute('INSERT INTO ms_obligations VALUES(?,?,?,?,?,?,?,?,?)',(identity,key,payee,due,amount,direction,kind,'pending',encode(detail)))


def next_obligation(c):
    if not installed(c):return None
    row=c.execute("SELECT min(due) FROM ms_obligations WHERE status='pending' AND CAST(substr(due,1,4) AS INTEGER) IN (SELECT season FROM ms_seasons WHERE state='preparing')").fetchone()
    return {'kind':'economic_due','kickoff':row[0]} if row and row[0] else None


def settle(c,a):
    required(a,'dated');market.advance_time(c,a['dated'])
    rows=c.execute("SELECT * FROM ms_obligations WHERE status='pending' AND due=? ORDER BY direction DESC,id",(a['dated'],)).fetchall()
    if not rows:raise ValueError('No unsettled economic group at that date')
    bonus_appearances=Counter()
    if any(r['kind']=='performance_bonus' for r in rows):
        for result in c.execute("SELECT x.result_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture WHERE f.status='final' AND f.kickoff<=? AND substr(f.kickoff,1,4)=?",(a['dated'],a['dated'][:4])):
            for p in json.loads(result[0])['performances']:
                if p['seconds_played']>0:bonus_appearances[(p['player_id'],p['club_key'])]+=1
    for r in rows:
        detail=json.loads(r['detail_json'])
        if r['kind']=='expiry':
            contract=c.execute("SELECT * FROM ms_contracts WHERE id=? AND status='active'",(detail['contract'],)).fetchone()
            if contract and contract['ends']<a['dated'][:10]:release(c,contract['player'],a['dated'][:10],'expiry')
        elif r['kind']=='performance_bonus' and bonus_appearances[(detail['player'],r['club'])]<detail['appearances']:
            c.execute("UPDATE ms_obligations SET status='not_triggered' WHERE id=?",(r['id'],));continue
        elif r['direction']==1:
            c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(r['amount_cents'],r['club']))
            c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(r['id'],r['club'],a['dated'],r['amount_cents'],r['kind'],r['detail_json']))
        else:
            market.debit(c,r['club'],r['amount_cents'],a['dated'],r['kind'],r['id'],detail)
            if r['payee']:
                c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(r['amount_cents'],r['payee']))
                c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(r['id']+':receipt',r['payee'],a['dated'],r['amount_cents'],r['kind'],r['detail_json']))
        c.execute("UPDATE ms_obligations SET status='settled' WHERE id=?",(r['id'],))
    return {'dated':a['dated'],'obligations_settled':len(rows),'canonical_approval':False}


def release(c,pid,dated,reason):
    p=c.execute('SELECT * FROM world_players WHERE id=?',(pid,)).fetchone()
    if not p:raise ValueError('Unknown player')
    attrs=json.loads(p['attributes_json'])
    retired=any(str(r).startswith('forward retirement ') for r in attrs['exclusion_reasons'])
    if not attrs['eligible'] and reason!='expiry':raise ValueError('Archived or retired player cannot be released into the market')
    con=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(pid,)).fetchone()
    if con and con['ends']>=dated:raise ValueError('Cannot release guaranteed future wages without a compensation policy')
    if con:c.execute("UPDATE ms_contracts SET status='expired' WHERE id=?",(con['id'],))
    value=state(c,pid);value['registered']=False;save_state(c,pid,value)
    c.execute('UPDATE ms_lifecycle SET status=? WHERE player=?',('retired' if retired else 'free_agent',pid))
    note(c,int(dated[:4]),p['club_key'],pid,reason,{'dated':dated,'historical_contract_unchanged':True})


def contract(c,pid,key,dated,ends,amount,source):
    old=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(pid,)).fetchone()
    if old:
        if old['starts']>dated:raise ValueError('Cannot overwrite future contract')
        if old['starts']==dated:
            if json.loads(old['provenance_json']).get('policy')!=POLICY:raise ValueError('Cannot annul an inherited same-day contract')
            c.execute("UPDATE ms_contracts SET status='annulled' WHERE id=?",(old['id'],))
        elif old['ends']>=dated:c.execute("UPDATE ms_contracts SET ends=?,status='superseded' WHERE id=?",((date.fromisoformat(dated)-timedelta(days=1)).isoformat(),old['id']))
        else:c.execute("UPDATE ms_contracts SET status='expired' WHERE id=?",(old['id'],))
    identity=f'off-contract:{pid}:{dated}:{key}'
    c.execute('INSERT INTO ms_contracts VALUES(?,?,?,?,?,?,?,?)',(identity,pid,key,dated,ends,amount,'active',encode(source)))
    s=state(c,pid);s.update(contract_start=dated,contract_end=ends,registered=True);save_state(c,pid,s)
    c.execute("UPDATE ms_lifecycle SET status='active' WHERE player=?",(pid,))
    obligation(c,identity+':expiry',key,None,(date.fromisoformat(ends)+timedelta(days=1)).isoformat()+' 00:00:00',0,0,'expiry',{'contract':identity})
    return identity


def configure(c,a):
    required(a,'season policy dated economics')
    year=a['season'];dated=a['dated']
    if not installed(c) or a['policy']!=POLICY or dated!=f'{year}-01-01':raise ValueError('Explicit installed offseason and January opening required')
    market.advance_time(c,dated+' 00:00:00')
    if c.execute('SELECT 1 FROM ms_offseasons WHERE season=?',(year,)).fetchone():raise ValueError('Offseason already committed')
    if not isinstance(a['economics'],dict) or not a['economics']:raise ValueError('Explicit economic scenarios required')
    c.execute('INSERT INTO ms_offseasons VALUES(?,?,?,\'open\',NULL)',(year,POLICY,dated))
    for key,s in sorted(a['economics'].items()):
        club(c,key);required(s,'reason opening_liquidity_cents monthly_income_cents monthly_cost_cents annual_wage_cap_cents fee_cap_cents additional_wage_cents')
        if not isinstance(s['reason'],str) or len(s['reason'])<15:raise ValueError('Economic uncertainty must be explained')
        for name,value in s.items():
            if name!='reason':market.money(value)
        if key=='club:15' and s['opening_liquidity_cents']:raise ValueError('No hypothetical opening capital for Vasco')
        if not c.execute('SELECT 1 FROM ms_accounts WHERE club=?',(key,)).fetchone():market.apply(c,'open_recorded_account',{'club':key})
        c.execute('INSERT INTO ms_economics VALUES(?,?,?)',(key,year,encode({**s,'canonical_approval':False,'policy':POLICY})))
        if key!='club:15':
            if year>2028 and s['opening_liquidity_cents']:raise ValueError('Initial modeled liquidity cannot replenish later seasons')
            if s['opening_liquidity_cents']:
                identity=f'TEST-opening:{key}:{year}'
                c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(s['opening_liquidity_cents'],key))
                c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(identity,key,dated,s['opening_liquidity_cents'],'TEST hypothetical opening liquidity',encode(s)))
            c.execute('UPDATE ms_accounts SET fee_authority_cents=?,wage_authority_cents=? WHERE club=?',(s['fee_cap_cents'],s['additional_wage_cents'],key))
        for month in range(1,13):
            due=f'{year}-{month:02}-01 00:00:00'
            for direction,kind,amount in ((1,'TEST modeled operating revenue',s['monthly_income_cents']),(-1,'TEST modeled recurring costs',s['monthly_cost_cents'])):
                if amount:obligation(c,f'economics:{key}:{year}-{month:02}:{direction}',key,None,due,amount,direction,kind,{'policy':POLICY,'scenario':s,'not_observed_revenue':True})
    return {'season':year,'clubs':len(a['economics']),'policy':POLICY,'canonical_approval':False}


def youth(c,key,year,index,position,dated,strength):
    from dataclasses import asdict
    from ..engine.models import Player
    from ..world.rosters import stable_id
    r=rng(c,'youth',key,year,index);pid=stable_id(f'offseason-youth:{key}:{year}',index)
    if c.execute('SELECT 1 FROM world_players WHERE id=?',(pid,)).fetchone():raise ValueError('Youth identity collision')
    ovr=round(max(45,min(75,strength-17+r.gauss(0,4))),2)
    p=Player(pid,key,f'Fictional academy {year} {key} {index}',position,ovr,ovr,ovr,ovr,ovr,ovr,ovr if position=='GK' else 20,100,65)
    provenance={'policy':POLICY,'source':'fictional forward youth intake','dated':dated,'canonical_approval':False}
    c.execute('INSERT INTO world_players VALUES(?,?,?,?,?,?)',(pid,key,None,1,encode(asdict(p)),encode(provenance)))
    s={'fitness':100,'morale':65,'form':6.55,'observed_at':dated+' 00:00:00','last_played':None,'injury_until':None,'injury_unknown':False,'registered':False,'contract_start':None,'contract_end':None,'recent':[]}
    c.execute('INSERT INTO world_player_state VALUES(?,?)',(pid,encode(s)))
    c.execute('INSERT INTO ms_lifecycle VALUES(?,?,?,\'active\',?)',(pid,17+r.randrange(3),year,encode(provenance)))
    note(c,year,key,pid,'youth_intake',provenance)
    return pid


def evolve(c,year,dated,clubs):
    changed=retired=intakes=0
    for p in c.execute('SELECT * FROM world_players ORDER BY id').fetchall():
        if p['club_key'] not in clubs:continue
        attrs=json.loads(p['attributes_json'])
        if not attrs['eligible']:continue
        old=c.execute('SELECT * FROM ms_lifecycle WHERE player=?',(p['id'],)).fetchone()
        r=rng(c,'development',year,p['id'])
        source=c.execute('SELECT career_phase,potential FROM players WHERE id=?',(p['source_id'],)).fetchone() if p['source_id'] else None
        if old:
            if old['observed_season']>=year:raise ValueError('Lifecycle already consumed')
            age=old['age']+year-old['observed_season']
            c.execute('UPDATE ms_lifecycle SET age=?,observed_season=? WHERE player=?',(age,year,p['id']))
        else:
            phase=str(source[0]).lower() if source else ''
            age=(20 if 'young' in phase or 'prospect' in phase else 35 if 'veteran' in phase else 22+r.randrange(14))
            c.execute('INSERT INTO ms_lifecycle VALUES(?,?,?,\'active\',?)',(p['id'],age,year,encode({'age':'explicit modeled age prior; no historical birthdate asserted','policy':POLICY})))
        con=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(p['id'],)).fetchone()
        if age>=35 and (not con or con['ends']<dated) and r.random()<min(.8,(age-33)*.12):
            s=state(c,p['id']);s['registered']=False;save_state(c,p['id'],s)
            attrs['eligible']=False;attrs['exclusion_reasons']=['forward retirement '+dated]
            c.execute('UPDATE world_players SET attributes_json=? WHERE id=?',(encode(attrs),p['id']))
            c.execute("UPDATE ms_lifecycle SET status='retired' WHERE player=?",(p['id'],));note(c,year,p['club_key'],p['id'],'retirement',{'age':age,'dated':dated});retired+=1;continue
        delta=round(max(-2.0,min(2.0,r.gauss(.7 if age<23 else -.7 if age>=31 else .1,.35))),3)
        after=dict(attrs)
        for name in ('ovr','attack','defense','passing','physical','composure','goalkeeping'):after[name]=round(max(15,min(95,attrs[name]+delta)),3)
        if source and source[1] and delta>0:after['ovr']=min(after['ovr'],max(attrs['ovr'],source[1]))
        c.execute('INSERT INTO ms_attributes VALUES(?,?,?,?,?)',(p['id'],year,encode(attrs),encode(after),encode({'policy':POLICY,'modeled_age':age,'delta':delta})))
        c.execute('UPDATE world_players SET attributes_json=? WHERE id=?',(encode(after),p['id']));changed+=1
    for key in sorted(clubs):
        strength=c.execute('SELECT strength FROM world_clubs WHERE key=?',(key,)).fetchone()[0]
        own=[json.loads(r[0]) for r in c.execute('SELECT attributes_json FROM world_players WHERE club_key=?',(key,)) if json.loads(r[0])['eligible']]
        counts=Counter(p['position'] for p in own)
        for i in range(1,3):
            pos=min(TARGETS,key=lambda x:(counts[x]/TARGETS[x],x));youth(c,key,year,i,pos,dated,strength);counts[pos]+=1;intakes+=1
    return {'developed':changed,'retired':retired,'youth':intakes}


def move(c,pid,buyer,dated,fee,new_wage,kind='purchase',loan_end=None):
    year=int(dated[:4]);p=c.execute('SELECT * FROM world_players WHERE id=?',(pid,)).fetchone();seller=p['club_key']
    if seller==buyer:raise ValueError('Cannot acquire own player')
    if c.execute("SELECT 1 FROM ms_loans WHERE player=? AND status='active'",(pid,)).fetchone():raise ValueError('Player already loaned')
    status=c.execute('SELECT status FROM ms_lifecycle WHERE player=?',(pid,)).fetchone()
    free=status and status[0]=='free_agent'
    if free:fee=0
    agent=fee//25;bonus=new_wage
    if not affordable(c,buyer,year,dated,fee,new_wage,agent+bonus+new_wage//2):raise ValueError('Unaffordable fee, future liabilities, wages or restricted reserve')
    identity=f'off-{kind}:{pid}:{dated}:{buyer}'
    if fee:
        upfront=fee*3//10
        market.debit(c,buyer,upfront,dated,'transfer upfront',identity+':upfront',{'total_fee_cents':fee})
        c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(upfront,seller))
        c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(identity+':seller',seller,dated,upfront,'transfer upfront',encode({'buyer':buyer})))
        obligation(c,identity+':installment',buyer,seller,f'{year}-07-01 00:00:00',fee-upfront,-1,'installment',{'transfer':identity})
    market.debit(c,buyer,agent+bonus,dated,'agent and signing bonus',identity+':costs',{'agent_cents':agent,'signing_bonus_cents':bonus})
    c.execute('UPDATE ms_accounts SET fee_authority_cents=fee_authority_cents-?,wage_authority_cents=wage_authority_cents-? WHERE club=?',(fee,new_wage*12,buyer))
    attrs=json.loads(p['attributes_json']);attrs['club_key']=buyer
    c.execute('UPDATE world_players SET club_key=?,attributes_json=? WHERE id=?',(buyer,encode(attrs),pid))
    detail={'policy':POLICY,'fee_cents':fee,'wage_cents':new_wage,'agent_cents':agent,'signing_bonus_cents':bonus,'dated':dated,'free_agent':bool(free)}
    obligation(c,identity+':bonus',buyer,None,f'{year}-12-21 23:59:00',new_wage//2,-1,'performance_bonus',{'player':pid,'appearances':10,'policy':POLICY})
    if kind=='loan':
        con=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(pid,)).fetchone()
        if not con or con['club']!=seller or con['ends']<loan_end or con['wage_cents']!=new_wage:raise ValueError('Loan requires an owned wage contract covering its full term and exact wage')
        c.execute('INSERT INTO ms_loans VALUES(?,?,?,?,?,?,?,\'active\')',(identity,pid,seller,buyer,dated,loan_end,10000))
        detail.update(option_fee_cents=fee*4,owner_wage_cents=con['wage_cents'],loan_end=loan_end)
    else:contract(c,pid,buyer,dated,f'{year+2}-12-31',new_wage,detail)
    s=state(c,pid);s['registered']=True;save_state(c,pid,s)
    c.execute('INSERT OR REPLACE INTO ms_registrations VALUES(?,?,?,\'registered\')',(year,pid,buyer))
    c.execute('INSERT INTO ms_transfers VALUES(?,?,?,?,?,?,?)',(identity,pid,None if free else seller,buyer,dated,kind,encode(detail)))
    note(c,year,buyer,pid,kind,{**detail,'transfer':identity,'seller':None if free else seller})
    return identity


def run(c,a):
    required(a,'season dated policy');year=a['season'];dated=a['dated']
    row=c.execute("SELECT * FROM ms_offseasons WHERE season=? AND state='open'",(year,)).fetchone()
    if not row or a['policy']!=POLICY or dated!=row['dated']:raise ValueError('Resume the exact configured offseason')
    market.advance_time(c,dated+' 00:00:00')
    clubs={r[0] for r in c.execute('SELECT club FROM ms_economics WHERE season=?',(year,))}
    evolution=evolve(c,year,dated,clubs)
    # Existing expired terms stay in history; release before making any offers.
    for con in c.execute("SELECT * FROM ms_contracts WHERE status='active' AND ends<? ORDER BY player",(dated,)).fetchall():release(c,con['player'],dated,'expiry')
    for p in c.execute('SELECT * FROM world_players ORDER BY id').fetchall():
        attrs=json.loads(p['attributes_json']);key=p['club_key']
        if key not in clubs or not attrs['eligible']:continue
        con=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(p['id'],)).fetchone()
        lifecycle=c.execute('SELECT status FROM ms_lifecycle WHERE player=?',(p['id'],)).fetchone()[0]
        if con:
            if con['club']!=key:continue # borrower cannot renew/replace the owner's contract
            if con['ends'][:4]==str(year) and rng(c,'renewal',year,p['id']).random()<.7:
                contract(c,p['id'],key,dated,f'{year+2}-12-31',con['wage_cents'],{'policy':POLICY,'renewal':'same known wage'})
                note(c,year,key,p['id'],'renewal',{'wage_cents':con['wage_cents']})
            continue
        if lifecycle=='free_agent':
            previous=c.execute("SELECT * FROM ms_contracts WHERE player=? AND ends<? ORDER BY ends DESC LIMIT 1",(p['id'],dated)).fetchone()
            if previous and rng(c,'expired-renewal',year,p['id']).random()<.85:
                amount=previous['wage_cents']
                if active_wages(c,key,dated)*12+amount*12<=budget(c,key,year)['annual_wage_cap_cents']:
                    contract(c,p['id'],key,dated,f'{year+2}-12-31',amount,{'policy':POLICY,'source':'negotiated free-agent renewal with former club; no past terms changed'})
                    note(c,year,key,p['id'],'renewal',{'wage_cents':amount,'expired_free_agent':True})
            continue
        if state(c,p['id']).get('contract_end') and state(c,p['id'])['contract_end']<dated:
            # Forward release of a weak surplus player; unknown past terms stay
            # unknown. Decisions are player/season streams, not outcome searches.
            depth=c.execute('SELECT count(*) FROM world_players WHERE club_key=?',(key,)).fetchone()[0]
            if depth>24 and attrs['position']!='GK' and rng(c,'release',year,p['id']).random()<.025:
                release(c,p['id'],dated,'release');continue
        amount=wage(attrs)
        if active_wages(c,key,dated)*12+amount*12>budget(c,key,year)['annual_wage_cap_cents']:raise ValueError('Initial modeled wage assumption exceeds explicit club cap')
        contract(c,p['id'],key,dated,f'{year+rng(c,"initial-term",year,p["id"]).randrange(2)}-12-31',amount,{'policy':POLICY,'source':'explicit forward modeled terms; historical wages unknown'})
    # Snapshot scouting is shared; all bids compete before any ownership changes.
    players=[dict(p) for p in c.execute('SELECT * FROM world_players ORDER BY id')]
    profiles={p['id']:json.loads(p['attributes_json']) for p in players}
    lives={r['player']:dict(r) for r in c.execute('SELECT * FROM ms_lifecycle')}
    contracts={r['player']:dict(r) for r in c.execute("SELECT * FROM ms_contracts WHERE status='active'")}
    plans={};bids=defaultdict(list)
    for key in sorted(clubs):
        acc=market.account(c,key)
        if acc['cash_cents']-acc['reserve_cents']-payable(c,key)<2*active_wages(c,key,dated):raise ValueError('Initial wage obligations are insolvent under the supplied scenario')
        own=[profiles[p['id']] for p in players if p['club_key']==key and profiles[p['id']]['eligible'] and lives.get(p['id'],{}).get('status')=='active']
        counts=Counter(p['position'] for p in own);need=min(TARGETS,key=lambda x:(counts[x]/TARGETS[x],x))
        strength=c.execute('SELECT strength FROM world_clubs WHERE key=?',(key,)).fetchone()[0]
        strategy='develop' if strength<70 else 'contend'
        plans[key]={'need':need,'depth':dict(counts),'strategy':strategy,'manager':'Luan Braga' if key=='club:15' else 'autonomous club manager'}
        candidates=[]
        acc=market.account(c,key);scenario=budget(c,key,year);base_wages=active_wages(c,key,dated)
        cash=acc['cash_cents']-acc['reserve_cents']-payable(c,key)
        for p in players:
            attrs=profiles[p['id']]
            if p['club_key']==key or p['club_key'] not in clubs or not attrs['eligible'] or attrs['position']!=need:continue
            life=lives.get(p['id'])
            if not life or life['status']=='retired':continue
            age=life['age'];r=rng(c,'bid',year,key,p['id'])
            fee=0 if life['status']=='free_agent' else max(100000,int((attrs['ovr']-45)**2*100000))
            amount=wage(attrs);loan=(age<=22 and r.random()<.25 and life['status']!='free_agent')
            if loan:
                fee//=5
                con=contracts.get(p['id'])
                if not con:continue
                amount=con['wage_cents']
            if (fee>acc['fee_authority_cents'] or amount*12>acc['wage_authority_cents'] or
                (base_wages+amount)*12>scenario['annual_wage_cap_cents'] or cash<fee+fee//25+amount+2*(base_wages+amount)):continue
            score=attrs['ovr']+(4 if strategy=='develop' and age<=23 else 0)+r.uniform(-3,3)
            candidates.append((score,p['id'],fee,amount,loan))
        for score,pid,fee,amount,loan in sorted(candidates,reverse=True)[:2]:
            bids[pid].append((score,key,fee,amount,loan))
            note(c,year,key,pid,'offer_submitted',{'fee_cents':fee,'wage_cents':amount,'kind':'loan' if loan else 'purchase','score':score})
        note(c,year,key,None,'squad_plan',plans[key])
    signed=failed=0;acquisitions=Counter()
    for pid,offers in sorted(bids.items()):
        accepted=False
        for score,key,fee,amount,loan in sorted(offers,reverse=True):
            reason=None;p=c.execute('SELECT * FROM world_players WHERE id=?',(pid,)).fetchone()
            attrs=json.loads(p['attributes_json']);supply=[json.loads(r[0]) for r in c.execute('SELECT attributes_json FROM world_players WHERE club_key=?',(p['club_key'],)) if json.loads(r[0])['eligible']]
            free=c.execute('SELECT status FROM ms_lifecycle WHERE player=?',(pid,)).fetchone()[0]=='free_agent'
            if acquisitions[key]>=2:reason='plan_already_filled'
            elif not free and sum(x['position']==attrs['position'] for x in supply)<=TARGETS[attrs['position']]-1:reason='seller_depth_refusal'
            elif rng(c,'agreement',year,key,pid).random()>.65:reason='player_or_seller_refused'
            elif not affordable(c,key,year,dated,fee,amount,fee//25+amount):reason='funding_changed_after_competing_bids'
            if reason:note(c,year,key,pid,'offer_rejected',{'reason':reason,'fee_cents':fee,'competing_offers':len(offers)});failed+=1;continue
            move(c,pid,key,dated,fee,amount,'loan' if loan else 'purchase',f'{year}-06-30' if loan else None)
            acquisitions[key]+=1;signed+=1;accepted=True;break
        if not accepted:continue
    for key in sorted(clubs):
        # A first-choice auction can leave a club with one goalkeeper after
        # contract expiry. Negotiate with OTHER remaining free agents under the
        # same cash/wage limits; never renew a refused offer or invent a player.
        for contingency in range(3):
            actual=[dict(p) for p in c.execute("SELECT p.* FROM world_players p JOIN ms_lifecycle l ON l.player=p.id WHERE p.club_key=? AND l.status='active'",(key,)) if json.loads(p['attributes_json'])['eligible']]
            gks=sum(json.loads(p['attributes_json'])['position']=='GK' for p in actual)
            if len(actual)>=18 and gks>=2:break
            position='GK' if gks<2 else min(TARGETS,key=lambda pos:sum(json.loads(p['attributes_json'])['position']==pos for p in actual)/TARGETS[pos])
            candidates=[]
            for p in c.execute("SELECT p.* FROM world_players p JOIN ms_lifecycle l ON l.player=p.id WHERE l.status='free_agent' AND p.club_key<>? ORDER BY p.id",(key,)):
                attrs=json.loads(p['attributes_json'])
                if not attrs['eligible'] or attrs['position']!=position:continue
                if c.execute("SELECT 1 FROM ms_market_decisions WHERE season=? AND club=? AND player=? AND kind IN ('offer_submitted','registration_offer_rejected')",(year,key,p['id'])).fetchone():continue
                amount=wage(attrs)
                if affordable(c,key,year,dated,0,amount,amount+amount//2):candidates.append((attrs['ovr'],p['id'],amount))
            agreed=False
            for _,pid,amount in sorted(candidates,reverse=True)[:10]:
                if rng(c,'registration-contingency-1',year,key,pid).random()>.65:
                    note(c,year,key,pid,'registration_offer_rejected',{'policy':'registration-contingency-1','wage_cents':amount});failed+=1;continue
                move(c,pid,key,dated,0,amount)
                note(c,year,key,pid,'registration_contingency',{'policy':'registration-contingency-1','need':position,'wage_cents':amount})
                signed+=1;agreed=True;break
            if not agreed:break
        for p in c.execute('SELECT * FROM world_players WHERE club_key=? ORDER BY id',(key,)):
            registered=json.loads(p['attributes_json'])['eligible'] and c.execute("SELECT 1 FROM ms_lifecycle WHERE player=? AND status='active'",(p['id'],)).fetchone() is not None
            s=state(c,p['id']);s['registered']=bool(registered);save_state(c,p['id'],s)
            c.execute('INSERT OR REPLACE INTO ms_registrations VALUES(?,?,?,?)',(year,p['id'],key,'registered' if registered else 'excluded'))
        eligible=[json.loads(r[0]) for r in c.execute('SELECT p.attributes_json FROM world_players p JOIN ms_registrations r ON r.player=p.id WHERE r.season=? AND r.club=? AND r.status=\'registered\'',(year,key))]
        if len(eligible)<18 or sum(p['position']=='GK' for p in eligible)<2:raise ValueError(f'Offseason leaves an impossible eligible squad: {key}; players={len(eligible)}, goalkeepers={sum(p["position"]=="GK" for p in eligible)}')
    summary={'policy':POLICY,'season':year,'clubs_planned':len(clubs),'signed':signed,'rejected':failed,**evolution,'canonical_approval':False,'production_authorized':False}
    c.execute("UPDATE ms_offseasons SET state='registered',summary_json=? WHERE season=?",(encode(summary),year))
    return summary


def apply(c,kind,a):
    if kind=='install_offseason':return install(c,a)
    if not installed(c):raise ValueError('Install the explicit TEST offseason migration first')
    if kind=='configure_offseason':return configure(c,a)
    if kind=='run_offseason':return run(c,a)
    if kind=='settle_economics':return settle(c,a)
    if kind=='reconcile_registrations':
        required(a,'season')
        if not c.execute('SELECT 1 FROM ms_offseasons WHERE season=?',(a['season'],)).fetchone():raise ValueError('No configured registration season')
        count=0
        for p in c.execute('SELECT * FROM world_players ORDER BY id'):
            s=state(c,p['id']);registered=s['registered'] and json.loads(p['attributes_json'])['eligible']
            c.execute('INSERT OR REPLACE INTO ms_registrations VALUES(?,?,?,?)',(a['season'],p['id'],p['club_key'],'registered' if registered else 'excluded'));count+=1
        return {'season':a['season'],'registration_rows_reconciled':count}
    if kind=='release_player':
        required(a,'player dated');market.advance_time(c,a['dated']+' 00:00:00')
        release(c,a['player'],a['dated'],'release')
        return {'player':a['player'],'status':'free_agent'}
    if kind=='exercise_loan_option':
        required(a,'loan dated');dated=a['dated']
        if date.fromisoformat(dated).month not in (1,2,7):raise ValueError('Outside registration window')
        market.advance_time(c,dated+' 00:00:00')
        loan=c.execute("SELECT * FROM ms_loans WHERE id=? AND status='active'",(a['loan'],)).fetchone()
        transfer=c.execute('SELECT detail_json FROM ms_transfers WHERE id=?',(a['loan'],)).fetchone()
        if not loan or not transfer or not loan['starts']<dated<=loan['ends']:raise ValueError('No active unexpired purchase option')
        terms=json.loads(transfer[0])
        if 'option_fee_cents' not in terms:raise ValueError('Loan has no committed option')
        p=c.execute('SELECT * FROM world_players WHERE id=?',(loan['player'],)).fetchone()
        if p['club_key']!=loan['borrower']:raise ValueError('Loan ownership changed')
        c.execute("UPDATE ms_loans SET ends=?,status='exercised' WHERE id=?",((date.fromisoformat(dated)-timedelta(days=1)).isoformat(),loan['id']))
        attrs=json.loads(p['attributes_json']);attrs['club_key']=loan['owner']
        c.execute('UPDATE world_players SET club_key=?,attributes_json=? WHERE id=?',(loan['owner'],encode(attrs),loan['player']))
        identity=move(c,loan['player'],loan['borrower'],dated,terms['option_fee_cents'],terms['owner_wage_cents'])
        return {'loan':loan['id'],'purchase':identity,'committed_option_exercised':True}
    raise ValueError('Unsupported offseason command')


def development_economics(c,year,clubs=None):
    """Read-only scenario builder, NEVER an observation or authorization.

    All amounts use fictional BRL units, including foreign clubs. No real-world
    wealth/exchange rate is imported. Caller must commit these explicit inputs.
    Vasco receives no opening capital or renewed transfer/wage authority.
    """
    result={};dated=f'{year}-01-01'
    for row in c.execute('SELECT * FROM world_clubs ORDER BY key'):
        key=row['key']
        if clubs is not None and key not in clubs:continue
        people=[dict(r) for r in c.execute('SELECT * FROM world_players WHERE club_key=? ORDER BY id',(key,)) if json.loads(r['attributes_json'])['eligible']]
        if len(people)<11:continue
        base=0
        for p in people:
            con=c.execute("SELECT wage_cents FROM ms_contracts WHERE player=? AND status='active' AND ends>=?",(p['id'],dated)).fetchone()
            base+=con[0] if con else wage(json.loads(p['attributes_json']))
        base+=2000000 # explicit reserve for two modeled youth wages
        acc=c.execute('SELECT * FROM ms_accounts WHERE club=?',(key,)).fetchone()
        additional=acc['wage_authority_cents'] if key=='club:15' and acc else base*3
        cash=acc['cash_cents']-acc['reserve_cents'] if acc else 0
        costs=base//8
        result[key]={'reason':'NONCANONICAL hypothetical all-club BRL economics: unknown base wages/wealth modeled prospectively; no real sponsor or owner capital claim',
            'opening_liquidity_cents':base*6 if year==2028 and key!='club:15' else 0,
            'monthly_income_cents':base*14//10+costs,'monthly_cost_cents':costs,
            'annual_wage_cap_cents':base*12+additional,'fee_cap_cents':min(base*3,max(0,cash//2)) if year>2028 else base*3,
            'additional_wage_cents':additional}
    return result
