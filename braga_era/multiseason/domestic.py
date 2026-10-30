"""Explicit proposed domestic formats, sharing the existing edition/engine store.

No historical brackets/results are imported. Entry evidence and every future draw
are committed by signed operations; all policy defaults remain NONCANONICAL.
"""
from datetime import datetime,timedelta
import json
import random
from ..history import digest,canonical_json as encode
from .competitions import required,club,brazilian,insert_fixture,standings

POLICY='domestic-ecosystem-development-1'
STATES=('SP','RJ','MG','RS','PR','SC','GO','CE','BA','PE','PA','RN','AL','MA','PB','PI','AM','SE','DF','MT','MS','ES','RO','TO','AC','AP','RR')
STATE_COMPETITIONS={f'STATE_{uf}' for uf in STATES if uf!='RJ'}
FORMATS={'cdb_128','carioca_12','state_knockout','domestic_supercup'}
CDB_SIZES={1:36,2:84,3:48,4:24,5:32,6:16,7:8,8:4,9:2}
CDB_LEGS={stage:2 if 5<=stage<=8 else 1 for stage in CDB_SIZES}
CDB_MATCHES=sum(CDB_SIZES[s]//2*CDB_LEGS[s] for s in CDB_SIZES)


def evidence(c,season,competition,key,source):
    """Validate future entry, retaining unknown 2027 state/B facts as proposals."""
    club(c,key)
    if competition!='RECOPA' and not brazilian(c,key):raise ValueError('Recorded or explicit modeled Brazilian club required')
    if not isinstance(source,dict):raise ValueError('Domestic qualification evidence required')
    kind=source.get('type')
    if kind=='development_administrative_scenario':
        required(source,'type id reason')
        if season!=2028 or not all(isinstance(source[x],str) and 3<=len(source[x])<=1000 for x in ('id','reason')):
            raise ValueError('Only the initial 2028 data gap accepts an explicit administrative scenario')
    elif kind=='current_serie_a':
        required(source,'type edition')
        if source['edition']!=f'LEAGUE:{season}' or not c.execute('SELECT 1 FROM ms_entries WHERE edition=? AND club=?',(source['edition'],key)).fetchone():
            raise ValueError('Current registered Série A entry required')
    elif kind=='edition_finish':
        required(source,'type edition position')
        row=c.execute('SELECT * FROM ms_editions WHERE id=?',(source['edition'],)).fetchone()
        if not row or row['state']!='completed' or row['season']!=season-1 or type(source['position']) is not int:
            raise ValueError('Completed adjacent-season sporting source required')
        ranked=final_order(c,row)
        if not 1<=source['position']<=len(ranked) or ranked[source['position']-1]!=key:raise ValueError('Sporting source identifies another club')
    elif kind=='prior_champion':
        required(source,'type competition')
        if season==2028:
            row=c.execute('SELECT club_key FROM world_champions WHERE competition=?',(source['competition'],)).fetchone()
        else:row=c.execute("SELECT champion FROM ms_editions WHERE competition=? AND season=? AND state='completed'",(source['competition'],season-1)).fetchone()
        if not row or row[0]!=key:raise ValueError('Prior recorded champion mismatch')
    else:raise ValueError('Unavailable domestic qualification evidence')


def create(c,a):
    required(a,'season competition policy entrants')
    if a['policy']!=POLICY or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Preparing season and versioned domestic proposal required')
    comp=a['competition'];entrants=a['entrants']
    if comp=='CDB':format='cdb_128';n=128
    elif comp=='CARIOCA':format='carioca_12';n=12
    elif comp in STATE_COMPETITIONS:format='state_knockout';n=len(entrants) if isinstance(entrants,list) else 0
    else:raise ValueError('Unsupported dedicated domestic competition')
    if not isinstance(entrants,list) or len(entrants)!=n or not 4<=n<=128:raise ValueError('Incorrect domestic participant inventory')
    if format=='state_knockout' and (n not in (8,16)):raise ValueError('Bounded state qualifier requires eight or sixteen clubs')
    keys=[]
    for entry in entrants:
        required(entry,'club phase source')
        if type(entry['phase']) is not int:raise ValueError('Integer entry phase required')
        evidence(c,a['season'],comp,entry['club'],entry['source']);keys.append(entry['club'])
    if len(set(keys))!=n:raise ValueError('Duplicate domestic club identity')
    if comp=='CARIOCA' or comp in STATE_COMPETITIONS:
        for key in keys:
            for existing in c.execute('SELECT e.competition FROM ms_entries x JOIN ms_editions e ON e.id=x.edition WHERE e.season=? AND x.club=?',(a['season'],key)):
                if existing[0]=='CARIOCA' or existing[0] in STATE_COMPETITIONS:raise ValueError('Club cannot enter multiple state federations in one season')
    if comp=='CDB':
        from collections import Counter
        if Counter(e['phase'] for e in entrants)!={1:36,2:66,3:6,5:20}:raise ValueError('CDB requires 102 state, six regional and twenty Série A routes')
        for e in entrants:
            if e['phase']==5 and e['source']['type']!='current_serie_a':raise ValueError('Late CDB entry requires actual registered Série A membership')
            if e['phase'] in (1,2) and e['source']['type']=='current_serie_a':raise ValueError('Série A cannot duplicate a state slot')
            if e['source']['type']=='edition_finish':
                prior=c.execute('SELECT competition FROM ms_editions WHERE id=?',(e['source']['edition'],)).fetchone()[0]
                if e['phase'] in (1,2) and prior!='CARIOCA' and prior not in STATE_COMPETITIONS:raise ValueError('CDB early entry requires recorded state qualification')
                if e['phase']==3 and (prior not in {'LOWER','NATIONAL_QUALIFIER','REGION_NE','REGION_N','REGION_CO','REGION_SS'} or e['source']['position']!=1):raise ValueError('CDB third-phase route requires an actual supported regional/access champion')
    elif any(e['phase']!=1 for e in entrants):raise ValueError('State entrants must begin in the group/first stage')
    edition=f'{comp}:{a["season"]}';rules={'legs':2,'final_legs':1,'neutral_final':True,'policy':POLICY}
    c.execute('INSERT INTO ms_editions VALUES(?,?,?,?,?,?,NULL)',(edition,comp,a['season'],format,encode(rules),'planned'))
    groups=None
    if comp=='CARIOCA':
        ordered=sorted(keys,key=lambda k:(-c.execute('SELECT strength FROM world_clubs WHERE key=?',(k,)).fetchone()[0],k))
        # Two balanced pots/groups, immutable in entries and signed create receipt.
        groups={'A':ordered[::2],'B':ordered[1::2]}
    for e in sorted(entrants,key=lambda e:e['club']):
        source={**e,'policy':POLICY}
        if groups:source['pool']=next(g for g in groups if e['club'] in groups[g])
        c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(f'{edition}:{e["club"]}',a['season'],comp,e['club'],encode(source)))
        c.execute('INSERT INTO ms_entries VALUES(?,?,?,?)',(edition,e['club'],'domestic_entry',encode(source)))
    return {'edition':edition,'policy':POLICY,'format':format,'participants':n,'groups':groups,'test_only':True,'canonical_policy_approved':False}


def create_supercup(c,a):
    required(a,'season competition policy')
    if a['policy']!=POLICY or a['competition'] not in {'SUPERCOPA','RECOPA'} or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Unsupported supercup policy or season')
    comps=('LEAGUE','CDB') if a['competition']=='SUPERCOPA' else ('LIB','SULA')
    participants=[]
    for comp in comps:
        if a['season']==2028:row=c.execute('SELECT club_key FROM world_champions WHERE competition=?',(comp,)).fetchone()
        else:row=c.execute("SELECT champion FROM ms_editions WHERE competition=? AND season=? AND state='completed'",(comp,a['season']-1)).fetchone()
        if not row or not row[0]:raise ValueError('Missing prior champion: '+comp)
        participants.append((row[0],{'type':'prior_champion','competition':comp}))
    if participants[0][0]==participants[1][0]:
        if a['competition']=='RECOPA':raise ValueError('Same-club Recopa title routes require an explicit exceptional policy; no opponent invented')
        if a['season']==2028:
            from ..world.adapters import recompute_standings
            table=recompute_standings(c,write=False)
            order=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
            if c.execute("SELECT count(*) FROM fixtures WHERE competition='Brasileirão 2027' AND status='final'").fetchone()[0]!=380:raise ValueError('League runner-up is not yet established')
            runner='club:'+str(order[1])
        else:
            row=c.execute("SELECT * FROM ms_editions WHERE competition='LEAGUE' AND season=? AND state='completed'",(a['season']-1,)).fetchone()
            if not row:raise ValueError('League runner-up is not yet established')
            runner=standings(c,row['id'])[1]['club']
        participants[1]=(runner,{'type':'recorded_league_runner_up','season':a['season']-1,'policy':POLICY})
    edition=f'{a["competition"]}:{a["season"]}';legs=2 if a['competition']=='RECOPA' else 1
    rules={'legs':legs,'final_legs':legs,'neutral_final':legs==1,'policy':POLICY}
    c.execute('INSERT INTO ms_editions VALUES(?,?,?,?,?,?,NULL)',(edition,a['competition'],a['season'],'domestic_supercup',encode(rules),'planned'))
    for key,source in participants:
        club(c,key)
        if a['competition']=='SUPERCOPA' and not brazilian(c,key):raise ValueError('Supercopa champion/runner-up lacks Brazilian identity evidence')
        c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(f'{edition}:{key}',a['season'],a['competition'],key,encode(source)))
        c.execute('INSERT INTO ms_entries VALUES(?,?,?,?)',(edition,key,source['type'],encode(source)))
    return {'edition':edition,'participants':[k for k,_ in participants],'sources':[s for _,s in participants],'policy':POLICY,'test_only':True}


def recorded_pools(c,e):
    entries={r['club']:json.loads(r['evidence_json']) for r in c.execute('SELECT * FROM ms_entries WHERE edition=? ORDER BY club',(e['id'],))}
    groups={g:{k for k,v in entries.items() if v.get('pool')==g} for g in ('A','B')}
    if any(len(g)!=6 for g in groups.values()) or groups['A']&groups['B']:raise ValueError('Invalid committed Carioca groups')
    receipt=None
    for op in c.execute("SELECT response_json FROM ms_operations WHERE kind='create_domestic_edition' ORDER BY sequence"):
        value=json.loads(op[0])
        if value['edition']==e['id']:receipt=value['groups'];break
    if receipt is None or {g:set(v) for g,v in receipt.items()}!=groups:raise ValueError('Carioca draw receipt and entries disagree')
    games=c.execute("SELECT * FROM ms_fixtures WHERE edition=? AND stage='POOL' ORDER BY key",(e['id'],)).fetchall()
    if not games:return groups
    if len(games)!=36:raise ValueError('Carioca cross-pool schedule is incomplete')
    pairs=[]
    for f in games:
        pair=(f['home'],f['away']) if f['home'] in groups['A'] else (f['away'],f['home'])
        pairs.append(pair)
    if len(set(pairs))!=36 or set(pairs)!={(a,b) for a in groups['A'] for b in groups['B']}:raise ValueError('Carioca cross-pool inventory differs from committed groups')
    return groups


def pool_table(c,e,pool=None):
    groups=recorded_pools(c,e)
    keys=groups[pool] if pool is not None else groups['A']|groups['B']
    totals={k:dict(club=k,points=0,played=0,wins=0,draws=0,losses=0,gf=0,ga=0) for k in keys}
    games=c.execute("SELECT * FROM ms_fixtures WHERE edition=? AND stage='POOL' ORDER BY key",(e['id'],)).fetchall()
    if len(games)!=36 or any(f['status']!='final' for f in games):raise ValueError('Carioca cross-pool schedule is incomplete')
    for f in games:
        for key,gf,ga in ((f['home'],f['home_goals'],f['away_goals']),(f['away'],f['away_goals'],f['home_goals'])):
            if key not in totals:continue
            t=totals[key];t['played']+=1;t['wins']+=int(gf>ga);t['draws']+=int(gf==ga);t['losses']+=int(gf<ga);t['points']+=3 if gf>ga else int(gf==ga);t['gf']+=gf;t['ga']+=ga
    if any(t['played']!=6 for t in totals.values()):raise ValueError('Carioca group participation is inconsistent')
    return sorted(totals.values(),key=lambda t:(-t['points'],-t['wins'],-(t['gf']-t['ga']),-t['gf'],t['club']))


def schedule(c,e,start,deadline):
    entries=[dict(r) for r in c.execute('SELECT * FROM ms_entries WHERE edition=? ORDER BY club',(e['id'],))]
    ties=[dict(r) for r in c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage,key',(e['id'],))]
    if e['format']=='carioca_12' and e['state']=='planned':
        groups={g:[r['club'] for r in entries if json.loads(r['evidence_json'])['pool']==g] for g in ('A','B')}
        for round in range(6):
            for i,home in enumerate(groups['A']):
                away=groups['B'][(i+round)%6]
                if round%2:home,away=away,home
                when=(datetime.fromisoformat(start)+timedelta(days=4*round)).isoformat(sep=' ',timespec='minutes')
                insert_fixture(c,e['id'],'POOL',round+1,None,home,away,when,deadline)
        c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
        return {'edition':e['id'],'stage':'POOL','scheduled':36}
    if ties:
        stage=max(t['stage'] for t in ties)+1;previous=[t for t in ties if t['stage']==stage-1]
        if any(not t['winner'] for t in previous):raise ValueError('Previous domestic knockout stage unresolved')
        winners=[t['winner'] for t in previous]
    else:stage=1;winners=[]
    if e['format']=='cdb_128':
        if stage>9:raise ValueError('CDB final already completed')
        incoming=[r['club'] for r in entries if json.loads(r['evidence_json'])['phase']==stage]
        clubs=sorted(winners+incoming)
        if len(clubs)!=CDB_SIZES[stage] or len(set(clubs))!=len(clubs):raise ValueError('CDB stage entry dependency or qualifier collision')
        seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
        random.Random(int(digest({'seed':seed,'edition':e['id'],'stage':stage,'pool':clubs,'policy':POLICY}),16)).shuffle(clubs)
        pairings=list(zip(clubs[::2],clubs[1::2]));legs=CDB_LEGS[stage];label=f'C{stage}'
    elif e['format']=='carioca_12':
        if stage==1:
            a=pool_table(c,e,'A');b=pool_table(c,e,'B')
            pairings=[(b[3]['club'],a[0]['club']),(b[2]['club'],a[1]['club']),(a[3]['club'],b[0]['club']),(a[2]['club'],b[1]['club'])]
        elif stage==2:pairings=[(winners[0],winners[3]),(winners[1],winners[2])]
        elif stage==3:pairings=[tuple(winners)]
        else:raise ValueError('Carioca final already completed')
        legs=2 if stage==2 else 1;label=f'K{stage}'
    elif e['format']=='domestic_supercup':
        if ties:raise ValueError('Supercup has already been scheduled')
        pairings=[tuple(r['club'] for r in entries)];legs=2 if e['competition']=='RECOPA' else 1;label='TROPHY'
    else:
        clubs=winners or [r['club'] for r in entries]
        if len(clubs)==1:raise ValueError('State final already completed')
        pairings=list(zip(clubs[::2],clubs[1::2]));legs=1;label=f'K{stage}'
    for i,(home,away) in enumerate(pairings,1):
        tie=f'{e["id"]}:{label}:{i:03}'
        c.execute('INSERT INTO ms_ties VALUES(?,?,?,?,?,NULL)',(tie,e['id'],stage,home,away))
        for leg in range(1,legs+1):
            when=(datetime.fromisoformat(start)+timedelta(days=7*(leg-1))).isoformat(sep=' ',timespec='minutes')
            insert_fixture(c,e['id'],label,leg,tie,home if leg==1 else away,away if leg==1 else home,when,deadline)
    c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
    return {'edition':e['id'],'stage':label,'scheduled':len(pairings)*legs,'policy':POLICY}


def final_order(c,e):
    if e['format']=='league':return [r['club'] for r in standings(c,e['id'])]
    entries=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(e['id'],))]
    eliminated={key:0 for key in entries}
    for t in c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage,key',(e['id'],)):
        if not t['winner']:raise ValueError('Unresolved final classification')
        loser=t['club_b'] if t['winner']==t['club_a'] else t['club_a'];eliminated[loser]=t['stage']
    if not e['champion']:raise ValueError('Completed champion required for final classification')
    # Equal elimination stage: pool sporting order where recorded, then stable ID.
    pool={r['club']:i for i,r in enumerate(pool_table(c,e))} if e['format']=='carioca_12' else {}
    performances={r['club']:r for r in standings(c,e['id'])}
    def order(key):
        t=performances[key]
        return (-eliminated[key],pool.get(key,0),-t['points'],-t['wins'],-(t['gf']-t['ga']),-t['gf'],key)
    return [e['champion']]+sorted((k for k in entries if k!=e['champion']),key=order)


def close(c,e):
    games=c.execute('SELECT * FROM ms_fixtures WHERE edition=?',(e['id'],)).fetchall()
    ties=c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage DESC,key',(e['id'],)).fetchall()
    n=c.execute('SELECT count(*) FROM ms_entries WHERE edition=?',(e['id'],)).fetchone()[0]
    expected=CDB_MATCHES if e['format']=='cdb_128' else 45 if e['format']=='carioca_12' else 2 if e['format']=='domestic_supercup' and e['competition']=='RECOPA' else n-1
    if not games or len(games)!=expected or any(g['status']!='final' for g in games) or any(not t['winner'] for t in ties):raise ValueError('Incomplete domestic competition inventory')
    winner=ties[0]['winner']
    c.execute("UPDATE ms_editions SET state='completed',champion=? WHERE id=?",(winner,e['id']))
    e=dict(e);e.update(champion=winner,state='completed')
    return {'edition':e['id'],'champion':winner,'final_order':final_order(c,e),'fixtures':expected,'test_only':True}


def match_policy(e,f,single,decisive):
    final=(e['format']=='cdb_128' and f['stage']=='C9' or e['format']=='carioca_12' and f['stage']=='K3')
    return {'neutral':bool(single and (final or e['competition']=='SUPERCOPA')),'extra_time':bool(single and decisive and e['format']=='carioca_12' and final)}


def stage_label(format,stage,participants):
    if format=='cdb_128':return {'C1':'R1','C2':'R2','C3':'R3','C4':'R4','C5':'R32','C6':'R16','C7':'QF','C8':'SF','C9':'FINAL'}.get(stage,stage)
    if format=='carioca_12':return {'POOL':'GROUP','K1':'QF','K2':'SF','K3':'FINAL'}.get(stage,stage)
    if format=='domestic_supercup':return 'FINAL'
    if format=='state_knockout' and stage.startswith('K') and stage[1:].isdigit():return {2:'FINAL',4:'SF',8:'QF',16:'R16'}.get(participants//2**(int(stage[1:])-1),stage)
    return stage
