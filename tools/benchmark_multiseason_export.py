"""Measure a complete DEV verification/export/restore pipeline on fixed inputs.

Fixture TEST key only; cannot authenticate or operate the production authority.
Run baseline before changing implementation, then optimized on the same source.
"""
import argparse
import json
from pathlib import Path
import time

from braga_era.db import file_sha256,connect_read_only
from braga_era.history import digest
from braga_era.multiseason import store

TEST_KEY=b'TEST ONLY MULTISEASON AUTHORITY!!'*2


def run(source,destination,label):
    source=Path(source);destination=Path(destination)
    if destination.exists():raise ValueError('Use a fresh benchmark destination')
    destination.mkdir(parents=True)
    before={name:file_sha256(source/name) for name in ('database.sqlite','parent.sqlite','development.json')}
    stages={};wall=time.perf_counter();cpu=time.process_time()
    def measure(name,function):
        w=time.perf_counter();p=time.process_time();result=function()
        stages[name]={'wall_seconds':time.perf_counter()-w,'cpu_seconds':time.process_time()-p}
        print(name,stages[name],flush=True)
        return result
    verified=measure('independent_validation',lambda:store.validate(source,TEST_KEY))
    exported=measure('export',lambda:store.export(source,destination/'portable',TEST_KEY))
    restored=measure('independent_restoration',lambda:store.restore(destination/'portable',destination/'restored',TEST_KEY))
    assert verified==exported==restored and verified['independent_replay'] and not verified['acceptance_eligible']
    assert before=={name:file_sha256(source/name) for name in before}
    with connect_read_only(source/'database.sqlite') as c:
        results={r[0]:r[1] for r in c.execute('SELECT fixture,result_sha256 FROM ms_executions ORDER BY fixture')}
    package=destination/'portable'
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','label':label,'stages':stages,
            'total_wall_seconds':time.perf_counter()-wall,'total_cpu_seconds':time.process_time()-cpu,
            'source_files':before,'fixtures':len(results),'match_results_sha256':digest(results),
            'world_sha256':verified['world_sha256'],'independent_replay':True,'independent_restoration':True,
            'database_bytes':(source/'database.sqlite').stat().st_size,
            'portable_directory_bytes':sum(p.stat().st_size for p in package.iterdir()),
            'portable_files':{p.name:file_sha256(p) for p in package.iterdir()}}
    (destination/'timings.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('label','fixtures','total_wall_seconds','total_cpu_seconds')}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--label',choices=('baseline','optimized'),required=True)
    args=parser.parse_args();run(args.source,args.output,args.label)
