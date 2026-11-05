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


from braga_era.multiseason.lifecycle import scenario,dates,plans

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
    command('prepare_season',season=2028)
    from braga_era.multiseason.lifecycle import setup_2028
    prepared=setup_2028(target,command,
        lambda i:advance(target,KEY,request_id=str(uuid5(NAMESPACE_URL,seed+':bootstrap:'+str(i))),max_groups=1),
        include_continental=include_continental,with_offseason=with_offseason)
    calendar,offseason=prepared['calendar'],prepared['offseason']
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
