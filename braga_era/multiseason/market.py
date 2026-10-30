"""Conservative recorded-money market and bounded forward attribute observations.

Unknown all-club budgets are not made up. Such clubs can sell/receive recognized
cash but cannot buy or promise new wages without a later approved finance policy.
"""
import calendar
from datetime import date,datetime,timedelta
from decimal import Decimal,ROUND_HALF_UP
import json
import random
from ..history import canonical_json as encode,digest
from ..payroll import financial_statement,cents
from .competitions import required,club


def money(value):
    if type(value) is not int or value<0:raise ValueError('Money must be nonnegative integer cents')
    return value


def advance_time(c,dated):
    when=datetime.fromisoformat(dated)
    if when.tzinfo:raise ValueError('Naive fictional dates only')
    clock=datetime.fromisoformat(c.execute('SELECT clock FROM ms_meta').fetchone()[0])
    if when<clock:raise ValueError('Cannot backdate an economic operation')
    if not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(when.year,)).fetchone():raise ValueError('No preparing economic season')
    pending=c.execute("SELECT min(kickoff) FROM ms_fixtures WHERE status!='final'").fetchone()[0]
    if pending and datetime.fromisoformat(pending)<=when:raise ValueError('Earlier fixture must be completed before administration')
    obligation=next_obligation(c)
    if obligation and datetime.fromisoformat(obligation['kickoff'])<when:raise ValueError('Earlier administrative obligation must be processed first')
    c.execute('UPDATE ms_meta SET clock=?',(when.isoformat(sep=' ',timespec='seconds'),))


def account(c,key):
    row=c.execute('SELECT * FROM ms_accounts WHERE club=?',(key,)).fetchone()
    if not row:raise ValueError('Missing recorded account; no assumed spending money')
    return row


def debit(c,key,amount,dated,category,identity,evidence):
    row=account(c,key)
    if row['cash_cents']-amount<row['reserve_cents']:raise ValueError('Cash payment would breach restricted reserve')
    c.execute('UPDATE ms_accounts SET cash_cents=cash_cents-? WHERE club=?',(amount,key))
    c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(identity,key,dated,-amount,category,encode(evidence)))


def payroll_detail(c,period):
    year,month=map(int,period.split('-'));days=calendar.monthrange(year,month)[1]
    amounts={}
    for row in c.execute('SELECT * FROM ms_contracts ORDER BY id'):
        start,end=date.fromisoformat(row['starts']),date.fromisoformat(row['ends'])
        loans=[dict(r) for r in c.execute('SELECT * FROM ms_loans WHERE player=? ORDER BY starts',(row['player'],))]
        for d in range(1,days+1):
            day=date(year,month,d)
            if not start<=day<=end:continue
            matching=[r for r in loans if r['starts']<=day.isoformat()<=r['ends']]
            if len(matching)>1:raise ValueError('Overlapping loan obligations')
            loan=matching[0] if matching else None
            shares=[(row['club'],10000)] if not loan else [(loan['owner'],10000-loan['wage_share_bps']),(loan['borrower'],loan['wage_share_bps'])]
            for payer,bps in shares:
                amounts[payer]=amounts.get(payer,Decimal(0))+Decimal(row['wage_cents'])*bps/10000/days
    return {k:int(v.quantize(Decimal('1'),rounding=ROUND_HALF_UP)) for k,v in sorted(amounts.items()) if v}


def unpaid_periods(c,season):
    return [f'{season}-{m:02}' for m in range(1,13)
            if c.execute('SELECT 1 FROM ms_contracts WHERE wage_cents>0 AND starts<=? AND ends>=? LIMIT 1',
                (f'{season}-{m:02}-{calendar.monthrange(season,m)[1]}',f'{season}-{m:02}-01')).fetchone()
            and not c.execute('SELECT 1 FROM ms_payroll WHERE period=?',(f'{season}-{m:02}',)).fetchone()]


def next_obligation(c):
    years=[r[0] for r in c.execute('SELECT season FROM ms_seasons WHERE season>=2028')]
    events=[]
    for year in years:
        for period in unpaid_periods(c,year):
            y,m=map(int,period.split('-'))
            events.append({'kind':'payroll','kickoff':f'{y}-{m:02}-{calendar.monthrange(y,m)[1]} 23:59:00','period':period})
    for loan in c.execute("SELECT * FROM ms_loans WHERE status='active'"):
        dated=(date.fromisoformat(loan['ends'])+timedelta(days=1)).isoformat()
        events.append({'kind':'loan_return','kickoff':dated+' 00:00:00','loan':loan['id'],'dated':dated})
    for row in c.execute("SELECT * FROM ms_income WHERE status='proposed'"):
        events.append({'kind':'proposed_income','kickoff':row['due'],'income':row['id']})
    return min(events,key=lambda x:(x['kickoff'],encode(x))) if events else None


def apply(c,kind,a):
    if kind=='propose_income':
        required(a,'club season monthly_cents reason');account(c,a['club']);amount=money(a['monthly_cents'])
        if not amount or not isinstance(a['reason'],str) or not a['reason'].strip():raise ValueError('An explicit forward economic assumption is required')
        if not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('No preparing economic season')
        policy={'version':'TEST-forward-income-proposal-1','reason':a['reason'],'canonical_approval':False,'scope':'explicitly modelled future income; not an observed sponsor contract or owner capital'}
        clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
        for month in range(1,13):
            due=f"{a['season']}-{month:02}-01 00:00:00"
            if due<=clock:raise ValueError('Income proposal cannot invent past receipts')
            identity=f"proposed-income:{a['club']}:{a['season']}-{month:02}"
            c.execute('INSERT INTO ms_income VALUES(?,?,?,?,?,?)',(identity,a['club'],due,amount,encode(policy),'proposed'))
        return {'club':a['club'],'annual_modelled_income_cents':amount*12,'policy':policy,'production_authorized':False}
    if kind=='receive_income':
        required(a,'income');row=c.execute("SELECT * FROM ms_income WHERE id=? AND status='proposed'",(a['income'],)).fetchone()
        if not row:raise ValueError('No unconsumed explicit income proposal')
        advance_time(c,row['due'])
        c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(row['amount_cents'],row['club']))
        c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(row['id'],row['club'],row['due'],row['amount_cents'],'TEST proposed forward operating income',row['policy_json']))
        c.execute("UPDATE ms_income SET status='applied' WHERE id=?",(row['id'],))
        return {'income':row['id'],'applied_cents':row['amount_cents'],'proposed_not_canonical':True}
    if kind=='open_recorded_account':
        required(a,'club');club(c,a['club'])
        if a['club']=='club:15':
            f=financial_statement(c)
            budget={r['category']:cents(r['amount_brl'])-cents(r['spent_brl']) for r in f['budgets']}
            values=(f['restricted_cash_cents'],budget['Emergency reserve'],budget['Transfer fees'],budget['Incremental wages'])
            provenance={'source':'preserved finance_ledger/finance_budget','new_capital':False,'future_year_authority':'TEST proposal; review required'}
        else:
            values=(0,0,0,0)
            provenance={'source':'unknown opening wealth excluded; only subsequently recorded inflows usable','unknown_actual_balance':True,'new_capital':False}
        c.execute('INSERT INTO ms_accounts VALUES(?,?,?,?,?,?)',(a['club'],*values,encode(provenance)))
        return {'club':a['club'],'recognized_cash_cents':values[0],'provenance':provenance}
    if kind=='renew_contract':
        required(a,'player starts ends wage_cents')
        wage=money(a['wage_cents']);player=c.execute('SELECT * FROM world_players WHERE id=?',(a['player'],)).fetchone()
        if not wage:raise ValueError('A known professional contract needs positive wages')
        if not player or not json.loads(player['attributes_json'])['eligible']:raise ValueError('Unknown or archived player')
        start,end=date.fromisoformat(a['starts']),date.fromisoformat(a['ends'])
        if start>end or start<date.fromisoformat(c.execute('SELECT clock FROM ms_meta').fetchone()[0][:10]):raise ValueError('Invalid forward contract dates')
        acc=account(c,player['club_key'])
        if wage*12>acc['wage_authority_cents']:raise ValueError('Insufficient annual wage authority')
        existing=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(a['player'],)).fetchone()
        if existing:
            if start<=date.fromisoformat(existing['starts']):raise ValueError('Cannot overwrite settled contract interval')
            c.execute("UPDATE ms_contracts SET status='superseded',ends=? WHERE id=?",((start-timedelta(days=1)).isoformat(),existing['id']))
        identity=f"contract:{a['player']}:{start}"
        c.execute('INSERT INTO ms_contracts VALUES(?,?,?,?,?,?,?,?)',(identity,a['player'],player['club_key'],str(start),str(end),wage,'active',encode({'source':'explicit forward proposal'})))
        c.execute('UPDATE ms_accounts SET wage_authority_cents=wage_authority_cents-? WHERE club=?',(wage*12,player['club_key']))
        state=json.loads(c.execute('SELECT state_json FROM world_player_state WHERE player_id=?',(a['player'],)).fetchone()[0])
        prior_start=state.get('contract_start')
        state.update(contract_start=min(prior_start,str(start)) if existing and prior_start else str(start),contract_end=str(end))
        c.execute('UPDATE world_player_state SET state_json=? WHERE player_id=?',(encode(state),a['player']))
        return {'contract':identity,'annual_commitment_cents':wage*12}
    if kind in {'purchase','loan'}:
        required(a,'player buyer dated fee_cents wage_cents ends' if kind=='purchase' else 'player buyer dated fee_cents ends wage_share_bps')
        club(c,a['buyer']);fee=money(a['fee_cents']);dated=date.fromisoformat(a['dated']);end=date.fromisoformat(a['ends'])
        if not (dated.month in (1,2,7)) or end<dated:raise ValueError('Outside proposed transfer window or invalid end date')
        advance_time(c,a['dated']+' 00:00:00')
        player=c.execute('SELECT * FROM world_players WHERE id=?',(a['player'],)).fetchone()
        if not player or not json.loads(player['attributes_json'])['eligible'] or player['club_key']==a['buyer']:raise ValueError('Invalid player ownership/identity')
        if c.execute("SELECT 1 FROM ms_loans WHERE player=? AND status='active'",(a['player'],)).fetchone():raise ValueError('Player already loaned')
        seller=player['club_key'];buyer=account(c,a['buyer']);account(c,seller)
        contract=c.execute("SELECT * FROM ms_contracts WHERE player=? AND status='active'",(a['player'],)).fetchone()
        if kind=='loan':
            bps=money(a['wage_share_bps'])
            if bps>10000 or not contract or contract['club']!=seller:raise ValueError('Loan needs an owned known contract and valid wage share')
            annual=(contract['wage_cents']*12*bps+9999)//10000
        else:
            if not money(a['wage_cents']):raise ValueError('A known professional contract needs positive wages')
            annual=a['wage_cents']*12
        if fee>buyer['fee_authority_cents'] or annual>buyer['wage_authority_cents']:raise ValueError('Transfer exceeds recorded budget authority')
        identity=f"{kind}:{a['player']}:{dated}:{a['buyer']}"
        debit(c,a['buyer'],fee,str(dated),'transfer fee',identity+':debit',a)
        c.execute('UPDATE ms_accounts SET cash_cents=cash_cents+? WHERE club=?',(fee,seller))
        c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',(identity+':credit',seller,str(dated),fee,'transfer fee',encode(a)))
        c.execute('UPDATE ms_accounts SET fee_authority_cents=fee_authority_cents-?,wage_authority_cents=wage_authority_cents-? WHERE club=?',(fee,annual,a['buyer']))
        if kind=='loan':
            c.execute('INSERT INTO ms_loans VALUES(?,?,?,?,?,?,?,?)',(identity,a['player'],seller,a['buyer'],str(dated),str(end),a['wage_share_bps'],'active'))
        else:
            if contract:
                if dated<=date.fromisoformat(contract['starts']):raise ValueError('Sale would overwrite existing contract interval')
                c.execute("UPDATE ms_contracts SET ends=?,status='transferred' WHERE id=?",((dated-timedelta(days=1)).isoformat(),contract['id']))
            c.execute('INSERT INTO ms_contracts VALUES(?,?,?,?,?,?,?,?)',(identity,a['player'],a['buyer'],str(dated),str(end),a['wage_cents'],'active',encode(a)))
        attrs=json.loads(player['attributes_json']);attrs['club_key']=a['buyer']
        c.execute('UPDATE world_players SET club_key=?,attributes_json=? WHERE id=?',(a['buyer'],encode(attrs),a['player']))
        state=json.loads(c.execute('SELECT state_json FROM world_player_state WHERE player_id=?',(a['player'],)).fetchone()[0])
        if kind=='purchase':state.update(contract_start=str(dated),contract_end=str(end))
        c.execute('UPDATE world_player_state SET state_json=? WHERE player_id=?',(encode(state),a['player']))
        c.execute('INSERT INTO ms_transfers VALUES(?,?,?,?,?,?,?)',(identity,a['player'],seller,a['buyer'],str(dated),kind,encode(a)))
        return {'transfer':identity,'player':a['player'],'seller':seller,'buyer':a['buyer'],'fee_cents':fee}
    if kind=='return_loan':
        required(a,'loan dated');loan=c.execute("SELECT * FROM ms_loans WHERE id=? AND status='active'",(a['loan'],)).fetchone()
        if not loan or a['dated']<=loan['ends']:raise ValueError('Loan not due to return')
        advance_time(c,a['dated']+' 00:00:00')
        player=c.execute('SELECT * FROM world_players WHERE id=?',(loan['player'],)).fetchone()
        if player['club_key']!=loan['borrower']:raise ValueError('Loan registration changed unexpectedly')
        attrs=json.loads(player['attributes_json']);attrs['club_key']=loan['owner']
        c.execute('UPDATE world_players SET club_key=?,attributes_json=? WHERE id=?',(loan['owner'],encode(attrs),loan['player']))
        c.execute("UPDATE ms_loans SET status='returned' WHERE id=?",(loan['id'],))
        return {'loan':loan['id'],'returned_to':loan['owner'],'player':loan['player']}
    if kind=='pay_month':
        required(a,'period');year,month=map(int,a['period'].split('-'))
        if a['period']!=f'{year:04}-{month:02}' or year<2028:raise ValueError('Invalid new-profile payroll period')
        detail=payroll_detail(c,a['period']);old=c.execute('SELECT * FROM ms_payroll WHERE period=?',(a['period'],)).fetchone()
        if old:
            if json.loads(old['detail_json'])!=detail:raise ValueError('Payroll terms changed after payment')
            return {'period':a['period'],'paid':detail}
        when=f'{year}-{month:02}-{calendar.monthrange(year,month)[1]} 23:59:00';advance_time(c,when)
        for payer,amount in detail.items():debit(c,payer,amount,when,'contract wages',f'payroll:{a["period"]}:{payer}',detail)
        c.execute('INSERT INTO ms_payroll VALUES(?,?)',(a['period'],encode(detail)))
        return {'period':a['period'],'paid':detail}
    if kind=='evolve':
        required(a,'season')
        if not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('No preparing season')
        seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0];changed=0
        for p in c.execute('SELECT * FROM world_players ORDER BY id').fetchall():
            attrs=json.loads(p['attributes_json'])
            if not attrs['eligible']:continue
            if c.execute('SELECT 1 FROM ms_attributes WHERE player=? AND season=?',(p['id'],a['season'])).fetchone():raise ValueError('Annual development already consumed')
            rng=random.Random(int(digest({'seed':seed,'player':p['id'],'season':a['season'],'purpose':'bounded-development-1'}),16))
            source=c.execute('SELECT career_phase,potential FROM players WHERE id=?',(p['source_id'],)).fetchone() if p['source_id'] else None
            phase=str(source[0]).lower() if source else 'unknown'
            mean=.3 if 'young' in phase or 'prospect' in phase else -.3 if 'veteran' in phase else 0
            delta=round(max(-1.5,min(1.5,rng.gauss(mean,.45))),3)
            after=dict(attrs)
            for key in ('ovr','attack','defense','passing','physical','composure','goalkeeping'):
                after[key]=round(max(15,min(95,attrs[key]+delta)),3)
            if source and source[1] and delta>0:after['ovr']=min(after['ovr'],max(attrs['ovr'],source[1]))
            assumption={'version':'bounded-development-1','delta':delta,'age':'not recorded; no birth date invented','career_phase':phase}
            c.execute('INSERT INTO ms_attributes VALUES(?,?,?,?,?)',(p['id'],a['season'],encode(attrs),encode(after),encode(assumption)))
            c.execute('UPDATE world_players SET attributes_json=? WHERE id=?',(encode(after),p['id']));changed+=1
        return {'season':a['season'],'players_evolved':changed,'historical_attributes_unchanged':True}
    if kind=='autonomous_recruitment':
        required(a,'club dated max_fee_cents max_wage_cents')
        club(c,a['club']);acc=account(c,a['club'])
        cap=min(money(a['max_fee_cents']),acc['fee_authority_cents'],acc['cash_cents']-acc['reserve_cents'])
        wage=min(money(a['max_wage_cents']),acc['wage_authority_cents']//12)
        if not cap or not wage:return {'club':a['club'],'outcome':'no_authorized_funding','capital_created':False}
        own=[json.loads(r[0]) for r in c.execute('SELECT attributes_json FROM world_players WHERE club_key=?',(a['club'],))]
        targets={'GK':3,'DF':8,'MF':7,'FW':5};need=min(targets,key=lambda pos:sum(p['position']==pos for p in own)/targets[pos])
        candidates=[];seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
        for p in c.execute('SELECT * FROM world_players WHERE club_key<>? ORDER BY id',(a['club'],)):
            attrs=json.loads(p['attributes_json']);state=json.loads(c.execute('SELECT state_json FROM world_player_state WHERE player_id=?',(p['id'],)).fetchone()[0])
            if not attrs['eligible'] or attrs['position']!=need or state['injury_unknown'] or state['injury_until']:continue
            valuation=max(0,int((attrs['ovr']-55)*15000000))  # cents; explicit proposed valuation, no historical assertion.
            rng=random.Random(int(digest({'seed':seed,'buyer':a['club'],'player':p['id'],'dated':a['dated'],'purpose':'negotiation-1'}),16))
            if valuation<=cap and rng.random()<.4:candidates.append((attrs['ovr'],p['id'],valuation))
        if not candidates:return {'club':a['club'],'outcome':'no_affordable_agreed_offer','need':need,'capital_created':False}
        _,pid,fee=max(candidates)
        seller=c.execute('SELECT club_key FROM world_players WHERE id=?',(pid,)).fetchone()[0]
        if not c.execute('SELECT 1 FROM ms_accounts WHERE club=?',(seller,)).fetchone():apply(c,'open_recorded_account',{'club':seller})
        result=apply(c,'purchase',{'player':pid,'buyer':a['club'],'dated':a['dated'],'fee_cents':fee,'wage_cents':wage,'ends':a['dated'][:4]+'-12-31'})
        return {'outcome':'signed','autonomous_manager':'Luan Braga' if a['club']=='club:15' else 'recorded/modelled club manager',**result}
    raise ValueError('Unsupported market operation')
