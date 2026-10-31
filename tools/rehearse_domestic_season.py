"""NONCANONICAL shared-calendar domestic year; never loads production authority.

This reports its missing continental/state/offseason scope as an acceptance
blocker. It must not be presented as a complete all-competition 2028 rehearsal.
"""
import argparse
from collections import Counter
from datetime import datetime,timedelta
import json
from pathlib import Path
import time
from uuid import uuid5,NAMESPACE_URL
from braga_era.db import connect_read_only,file_sha256
from braga_era.history import digest
from braga_era.seasons import AcceptedSource
from braga_era.forward import sign
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance,next_event
from braga_era.multiseason.domestic import POLICY as DOMESTIC
from braga_era.multiseason.divisions import POLICY as DIVISIONS
from braga_era.multiseason.calendar import POLICY as CALENDAR

KEY=b'TEST ONLY DOMESTIC SEASON REHEARSAL, NEVER PRODUCTION'*2


def scenario(reason):return {'type':'development_administrative_scenario','id':'domestic-year-transition-1','reason':reason}


def dates(first,last):
    day=datetime.fromisoformat(first);end=datetime.fromisoformat(last);result=[]
    while day<=end:result.append(day.strftime('%Y-%m-%d %H:%M'));day+=timedelta(days=1)
    return result


def plans(year,include_continental=False):
    def one(stage,*values):return {'stage':stage,'command':'schedule','slots':{str(i):[f'{year}-{value} 16:00'] for i,value in enumerate(values,1)}}
    international=[[f'{year}-{start} 00:00',f'{year}-{end} 23:59'] for start,end in [('03-20','03-28'),('06-05','06-13'),('09-04','09-12'),('10-09','10-17')]]
    day=datetime(year,3,1)
    while day.weekday()!=6:day+=timedelta(days=1)
    sundays=[]
    while len(sundays)<38:
        value=day.strftime('%Y-%m-%d %H:%M').replace('00:00','16:00')
        if not any(a<=value<=b for a,b in international):sundays.append(value)
        day+=timedelta(days=7)
    def league(n):return [{'stage':'LEAGUE','command':'schedule','slots':{str(i):[d] for i,d in enumerate(sundays[:n],1)}}]
    calendar={f'LEAGUE:{year}':league(38),f'SERIE_B:{year}':league(38),f'LOWER:{year}':league(14)}
    if year==2028:
        calendar[f'ACCESS:{year}']=[one('S1','01-06','01-10')]
        calendar[f'CARIOCA:{year}']=[{'stage':'POOL','command':'schedule','slots':{str(i+1):dates((datetime(year,1,7,16)+timedelta(days=4*i)).strftime('%Y-%m-%d %H:%M'),f'{year}-02-01 16:00') for i in range(6)}},one('K1','02-04'),one('K2','02-11','02-18'),one('K3','02-25')]
        calendar[f'CDB:{year}']=[one('C1','02-07'),one('C2','02-21'),one('C3','03-15'),one('C4','04-05'),one('C5','05-10','05-17'),one('C6','07-05','07-12'),one('C7','08-09','08-16'),one('C8','09-20','09-27'),one('C9','11-22')]
        calendar[f'SUPERCOPA:{year}']=[one('TROPHY','01-06')]
        calendar[f'RECOPA:{year}']=[one('TROPHY','01-10','01-17')]
        if include_continental:
            calendar[f'LIB_PRE1:{year}']=[one('S1','01-24','01-31')]
            calendar[f'LIB_PRE2:{year}']=[one('S1','02-07','02-14')]
            calendar[f'LIB_PRE3:{year}']=[one('S1','02-21','02-28')]
            calendar[f'SULA_PRE:{year}']=[one('NATIONAL_PRE','03-08')]
            groups={'stage':'GROUP','command':'schedule_calendar_country_groups','slots':{str(i):[f'{year}-{date} 16:00'] for i,date in enumerate(('04-12','04-26','05-03','05-24','06-14','06-28'),1)}}
            calendar[f'LIB:{year}']=[groups,one('S1','08-02','08-23'),one('S2','09-13','10-04'),one('S3','11-01','11-08'),one('S4','11-29')]
            calendar[f'SULA:{year}']=[groups,one('PO','07-19','07-26'),one('S1','08-02','08-23'),one('S2','09-13','10-04'),one('S3','11-01','11-08'),one('S4','11-15')]
    return calendar,international


def run(source_path,output,*,seed='domestic-year-fixed-before-simulation-1',include_continental=False,with_offseason=False):
    start=time.perf_counter();source_path=Path(source_path);output=Path(output)
    with connect_read_only(source_path) as c:
        if c.execute('SELECT scope FROM world_info').fetchone()[0]!='NONCANONICAL DEVELOPMENT TEST':raise ValueError('Only a disconnected NONCANONICAL completed 2027 source is permitted')
    parent_hash=file_sha256(source_path);source=AcceptedSource(source_path.resolve(),'NONCANONICAL-completed-2027-fixture',parent_hash)
    target=output/'world'
    if not target.exists():
        policy=store.proposed_policy();decision=store.statement(source,policy,seed)
        store.create(source,target,seed=seed,policy=policy,decision=decision,signature=sign(KEY,decision),test_key=KEY)
    else:
        _,marker=store.authenticated(target,KEY)
        if marker['seed']!=seed or marker['parent']['database_sha256']!=parent_hash:raise ValueError('Cannot replace an existing rehearsal parent or seed')
    def command(kind,**args):return store.run(target,KEY,str(uuid5(NAMESPACE_URL,'domestic-year-1:'+seed+':'+kind+':'+digest(args))),kind,args)
    command('prepare_season',season=2028);command('open_recorded_account',club='club:15')
    if not with_offseason:
        command('propose_income',club='club:15',season=2028,monthly_cents=300000000,reason='Hypothetical TEST incremental operating-income scenario for known contracts; not real revenue, owner capital or approved finances')
        command('evolve',season=2028);command('continue_modeled_registrations',season=2028)
    command('carry_discipline',season=2028,policy='carry-unserved-bans-reset-yellows-1')
    def register(prefix,n):return [command('register_fictional_club',name=f'Fictional {prefix} {i:03}',strength=60+i%15,dated='2028-01-01')['club'] for i in range(n)]
    pool=register('Domestic State Entrant',108);access=register('Initial Access Entrant',8);b=register('Initial B Entrant',12);lower=register('Lower Path Entrant',8)
    if include_continental:
        from braga_era.multiseason.continental_policy import ALLOCATIONS
        from braga_era.multiseason.continental_entry import POLICY as ENTRY,SULA_SLOTS
        national={'BRA':{'type':'legacy_league_and_cup'}}
        for country,n in ALLOCATIONS.items():
            if country=='BRA':continue
            clubs=[command('register_fictional_club_country',country=country,name=f'Fictional Integrated {country} Entrant {i:02}',strength=80-i*.8,dated='2028-01-01')['club'] for i in range(n+SULA_SLOTS[country])]
            national[country]={**scenario('Explicit foreign entry-order scenario; missing historical national results remain unknown'),'clubs':clubs}
        with connect_read_only(target/'database.sqlite') as c:champions=[{'competition':comp,'club':c.execute('SELECT club_key FROM world_champions WHERE competition=?',(comp,)).fetchone()[0],'evidence':{'type':'legacy_champion'}} for comp in ('LIB','SULA')]
        command('commit_continental_entry',season=2028,policy=ENTRY,national_evidence=national,champions=champions)
    offseason=None
    if with_offseason:
        from braga_era.multiseason.offseason import POLICY as OFFSEASON,development_economics
        command('install_offseason',policy=OFFSEASON)
        with connect_read_only(target/'database.sqlite') as c:
            original=c.execute("SELECT args_json FROM ms_operations WHERE kind='configure_offseason' ORDER BY sequence LIMIT 1").fetchone()
            economics=json.loads(original[0])['economics'] if original else development_economics(c,2028)
        command('configure_offseason',season=2028,dated='2028-01-01',policy=OFFSEASON,economics=economics)
        command('settle_economics',dated='2028-01-01 00:00:00')
        offseason=command('run_offseason',season=2028,dated='2028-01-01',policy=OFFSEASON)
        print('NONCANONICAL autonomous offseason',offseason,flush=True)
    command('propose_pool',id='initial-access',season=2028,competition='ACCESS',clubs=access,reason='Explicit prospective 2028 transition, not fabricated 2027 Série B results')
    for key in access:command('qualify',season=2028,competition='ACCESS',club=key,source={'type':'proposed_pool','pool':'initial-access'})
    command('edition',competition='ACCESS',season=2028,format='qualification',clubs=access,rules={'legs':2,'final_legs':1,'neutral_final':False})
    with connect_read_only(target/'database.sqlite') as c:
        rio=['club:'+str(r[0]) for r in c.execute("SELECT id FROM clubs WHERE name IN ('Vasco','Flamengo','Fluminense','Botafogo') ORDER BY id")]
        venue_bindings={r[0]:'TEST assumed individual ground: '+r[0] for r in c.execute('SELECT key FROM world_clubs')}
    command('create_domestic_edition',season=2028,competition='CARIOCA',policy=DOMESTIC,entrants=[{'club':key,'phase':1,'source':scenario('Proposed RJ membership and fictional forward entrants, not claimed historical registration')} for key in rio+pool[:8]])
    for comp in ('SUPERCOPA','RECOPA'):command('create_supercup',season=2028,competition=comp,policy=DOMESTIC)
    calendar,windows=plans(2028,include_continental)
    for edition in calendar:venue_bindings['neutral:'+edition]='TEST proposed neutral final: '+edition
    command('commit_season_calendar',season=2028,policy=CALENDAR,plans=calendar,international_windows=windows,venues=venue_bindings)
    # Prior champions are already known: reserve their complete one/two-leg duty
    # before drawing state fixtures. Unknown future winners are never assigned.
    command('schedule',edition='SUPERCOPA:2028',start='2028-01-06 16:00',deadline='2028-01-06 16:00')
    command('schedule',edition='RECOPA:2028',start='2028-01-10 16:00',deadline='2028-01-17 16:00')
    for i in range(40):
        with connect_read_only(target/'database.sqlite') as c:
            done=c.execute("SELECT count(*) FROM ms_fixtures WHERE edition='ACCESS:2028' AND status='final'").fetchone()[0]
        if done==8:break
        advance(target,KEY,request_id=str(uuid5(NAMESPACE_URL,seed+':bootstrap:'+str(i))),max_groups=1)
    else:raise ValueError('Access transition failed to finish within bound')
    with connect_read_only(target/'database.sqlite') as c:closed=c.execute("SELECT state FROM ms_editions WHERE id='ACCESS:2028'").fetchone()[0]=='completed'
    if not closed:command('close_edition',edition='ACCESS:2028')
    with connect_read_only(target/'database.sqlite') as c:
        winners=[r[0] for r in c.execute("SELECT winner FROM ms_ties WHERE edition='ACCESS:2028' ORDER BY key")]
        from braga_era.world.adapters import recompute_standings
        table=recompute_standings(c,write=False)
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
    survivors=['club:'+str(k) for k in ranked[:16]]
    for pos,key in enumerate(survivors,1):command('qualify',season=2028,competition='LEAGUE',club=key,source={'type':'legacy_league_position','position':pos})
    for key in winners:command('qualify',season=2028,competition='LEAGUE',club=key,source={'type':'edition_qualifier','edition':'ACCESS:2028'})
    command('edition',competition='LEAGUE',season=2028,format='league',clubs=survivors+winners,rules={'legs':2,'final_legs':1,'neutral_final':False})
    losers=[k for k in access if k not in winners]
    command('register_divisions',season=2028,policy=DIVISIONS,initial_b=[{'club':k,'source':{'type':'access_eliminated','edition':'ACCESS:2028'}} for k in losers]+[{'club':k,'source':scenario('Initial missing 2027 Série B admission; no past sporting result asserted')} for k in b],initial_lower=[{'club':k,'source':scenario('Bounded forward lower-division access registration')} for k in lower])
    early=b+losers+pool[16:]
    command('create_domestic_edition',season=2028,competition='CDB',policy=DOMESTIC,entrants=[{'club':k,'phase':1 if i<36 else 2 if i<102 else 3,'source':scenario('Unapproved missing 2027 state/regional qualification scenario')} for i,k in enumerate(early)]+[{'club':k,'phase':5,'source':{'type':'current_serie_a','edition':'LEAGUE:2028'}} for k in survivors+winners])
    for i in range(20):
        if next_event(target,KEY) is None:break
        result=advance(target,KEY,request_id=str(uuid5(NAMESPACE_URL,seed+':season:'+str(i))),max_groups=100)
        with connect_read_only(target/'database.sqlite') as c:count=c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]
        print('verified engine fixtures persisted',count,'next kind',result['next_event']['kind'] if result['next_event'] else None,flush=True)
    else:raise ValueError('Season exceeded bounded agenda runs')
    required_competitions=[key.rsplit(':',1)[0] for key in calendar]
    if with_offseason:command('reconcile_registrations',season=2028)
    command('archive_season',season=2028,required_competitions=required_competitions)
    verification=store.validate(target,KEY)
    package=output/'portable'
    if not package.exists():store.export(target,package,KEY)
    if not (output/'restored').exists():store.restore(package,output/'restored',KEY)
    with connect_read_only(target/'database.sqlite') as c:
        counts=dict(c.execute('SELECT edition,count(*) FROM ms_fixtures GROUP BY edition'))
        championships=[dict(r) for r in c.execute('SELECT competition,state,champion FROM ms_editions ORDER BY competition')]
        from braga_era.multiseason.audit import season as audit_season
        reconciliation=audit_season(c,2028)
    expected=1341 if include_continental else 1029
    if sum(counts.values())!=expected or any(e['state']!='completed' for e in championships):raise ValueError('Incomplete declared competition inventory')
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','source_unchanged':file_sha256(source_path)==parent_hash,'fixture_counts':counts,'competitions':championships,'verification':verification,'elapsed_seconds':time.perf_counter()-start,'domestic_and_continental_integrated':include_continental,'complete_all_competition_2028':False,'blockers':(['Remaining non-RJ state calendars not yet included'] if include_continental else ['Continental and remaining state calendars not yet included in this scoped domestic run'])+['Complete all-club finances/offseason and production season-aware authority remain unimplemented'],'production_modified':False}
    report['reconciliation']=reconciliation
    report['offseason']=offseason
    if with_offseason:
        report['blockers']=['Remaining non-RJ state calendars and full federation qualification remain incomplete','Offseason/economic assumptions require calibration and commissioner policy acceptance','Production season-transition authority and season-aware phone bridge are not implemented']
    if not report['source_unchanged']:raise ValueError('Disconnected source changed')
    output.mkdir(parents=True,exist_ok=True);(output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--continental',action='store_true');p.add_argument('--offseason',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.db,a.output,include_continental=a.continental,with_offseason=a.offseason,seed='offseason-integrated-fixed-1' if a.offseason else 'domestic-year-fixed-before-simulation-1'),indent=2))
