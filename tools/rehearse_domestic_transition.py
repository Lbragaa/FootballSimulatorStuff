"""Restore a TEST 2028 package and prove actual division movement/2029 fixtures."""
import argparse
import json
from pathlib import Path
import time
from uuid import uuid5,NAMESPACE_URL
from braga_era.history import digest
from braga_era.db import connect_read_only,file_sha256
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance
from braga_era.multiseason.divisions import POLICY
from braga_era.multiseason.competitions import standings
from braga_era.multiseason.calendar import POLICY as CALENDAR
from tools.rehearse_domestic_season import KEY,plans


def run(package,output):
    start=time.perf_counter();package=Path(package);output=Path(output);target=output/'world'
    original={p.name:file_sha256(p) for p in package.iterdir()}
    if not target.exists():store.restore(package,target,KEY)
    def command(kind,**args):return store.run(target,KEY,str(uuid5(NAMESPACE_URL,'recorded-2029-transition-1:'+kind+':'+digest(args))),kind,args)
    with connect_read_only(target/'database.sqlite') as c:
        previous={r['competition']:[t['club'] for t in standings(c,r['id'])] for r in c.execute("SELECT * FROM ms_editions WHERE season=2028 AND competition IN ('LEAGUE','SERIE_B','LOWER')")}
        protected=[tuple(r) for r in c.execute("SELECT key,home_goals,away_goals,winner,status FROM ms_fixtures WHERE edition LIKE '%:2028' ORDER BY key")]
        receipts=[tuple(r) for r in c.execute("SELECT fixture,result_sha256 FROM ms_executions WHERE fixture LIKE 'ms:%:2028:%' ORDER BY fixture")]
    command('prepare_season',season=2029)
    command('propose_income',club='club:15',season=2029,monthly_cents=300000000,reason='Same explicit TEST incremental known-payroll scenario; not approved native revenue')
    command('continue_modeled_registrations',season=2029);command('evolve',season=2029)
    command('carry_discipline',season=2029,policy='carry-unserved-bans-reset-yellows-1')
    registered=command('register_divisions',season=2029,policy=POLICY,initial_b=[],initial_lower=[])
    moved=registered['divisions']
    assert set(moved['LEAGUE'])==set(previous['LEAGUE'][:16]+previous['SERIE_B'][:4])
    assert set(moved['SERIE_B'])==set(previous['LEAGUE'][16:]+previous['SERIE_B'][4:16]+previous['LOWER'][:4])
    assert set(moved['LOWER'])==set(previous['SERIE_B'][16:]+previous['LOWER'][4:])
    assert set(sum(moved.values(),[]))==set(sum(previous.values(),[]))
    command('carry_division_bans',season=2029,policy='follow-national-division-bans-1')
    with connect_read_only(target/'database.sqlite') as c:venues={r[0]:'TEST assumed individual ground: '+r[0] for r in c.execute('SELECT key FROM world_clubs')}
    calendar,windows=plans(2029)
    command('commit_season_calendar',season=2029,policy=CALENDAR,plans=calendar,international_windows=windows,venues=venues)
    request=str(uuid5(NAMESPACE_URL,'recorded-2029-first-two-groups'))
    result=advance(target,KEY,request_id=request,max_groups=2)
    assert advance(target,KEY,request_id=request,max_groups=2)==result
    with connect_read_only(target/'database.sqlite') as c:
        assert protected==[tuple(r) for r in c.execute("SELECT key,home_goals,away_goals,winner,status FROM ms_fixtures WHERE edition LIKE '%:2028' ORDER BY key")]
        assert receipts==[tuple(r) for r in c.execute("SELECT fixture,result_sha256 FROM ms_executions WHERE fixture LIKE 'ms:%:2028:%' ORDER BY fixture")]
        counts=dict(c.execute("SELECT edition,count(*) FROM ms_fixtures WHERE edition LIKE '%:2029' AND status='final' GROUP BY edition"))
        assert counts=={'LEAGUE:2029':20,'SERIE_B:2029':20,'LOWER:2029':8}
    report=store.validate(target,KEY)
    if not (output/'portable').exists():store.export(target,output/'portable',KEY)
    if not (output/'restored').exists():store.restore(output/'portable',output/'restored',KEY)
    assert original=={p.name:file_sha256(p) for p in package.iterdir()}
    result={'scope':'NONCANONICAL DEVELOPMENT TEST','new_clubs_created':False,'recorded_division_movement':True,'2029_completed_fixture_counts':counts,'all_2028_results_and_receipts_unchanged':True,'source_package_unchanged':True,'verification':report,'elapsed_seconds':time.perf_counter()-start,'complete_2029_ecosystem':False,'production_modified':False}
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.package,a.output),indent=2))
