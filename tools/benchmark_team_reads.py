"""Read-only identical-workload team loading benchmark; no football execution."""
import argparse,json,sys,time
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from braga_era.db import connect_read_only,file_sha256
from braga_era.history import digest
from braga_era.world.players import team_at
from braga_era.world.policy import ReadinessPolicy


def run(database,output,repetitions=30):
    before=file_sha256(database);queries=0
    with connect_read_only(database) as c:
        clubs=['club:'+str(r[0]) for r in c.execute('SELECT club_id FROM league_participants WHERE season=2027 ORDER BY club_id')]
        def trace(sql):
            nonlocal queries
            if sql.lstrip().upper().startswith('SELECT'):queries+=1
        c.set_trace_callback(trace);start=time.perf_counter();cpu=time.process_time()
        expected=None
        for _ in range(repetitions):
            teams=[asdict(team_at(c,k,'LEAGUE:2029','2029-01-06 16:00',ReadinessPolicy())) for k in clubs]
            value=digest(teams)
            if expected is not None and expected!=value:raise ValueError('Read state changed')
            expected=value
        result={'scope':'read-only disconnected development workload','clubs':len(clubs),'repetitions':repetitions,
                'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,
                'selects':queries,'teams_sha256':expected,'source_unchanged':file_sha256(database)==before}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.db,a.output)
