"""Paired full-history versus immediate-parent verification, TEST fixtures only."""
import argparse
import json
from pathlib import Path
import time
from braga_era.db import connect_read_only,file_sha256
from braga_era.multiseason import store,incremental
from tools.rehearse_domestic_season import KEY


def peak_memory():
    """Process peak RSS, not a resettable per-stage measurement."""
    import sys
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
        api=ctypes.WinDLL('psapi',use_last_error=True);api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):return None
        return counters.peak
    import resource
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform=='darwin' else value*1024


def run(parent_package,normal_child,destination):
    parent_package=Path(parent_package);normal_child=Path(normal_child);destination=Path(destination)
    if destination.exists():raise ValueError('Use a fresh benchmark destination')
    destination.mkdir(parents=True);timings={}
    source={name:file_sha256(normal_child/name) for name in ('database.sqlite','parent.sqlite','development.json')}
    def measure(name,function):
        wall=time.perf_counter();cpu=time.process_time();result=function()
        timings[name]={'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu}
        print(name,timings[name],flush=True);return result
    parent=measure('one_time_parent_seal',lambda:incremental.seal_parent(parent_package,destination/'sealed',KEY))
    measure('create_exact_parent_child',lambda:incremental.create(destination/'sealed',destination/'child',KEY))
    with connect_read_only(normal_child/'database.sqlite') as c:
        suffix=[dict(r) for r in c.execute('SELECT * FROM ms_operations WHERE sequence>? ORDER BY sequence',(parent['operations'],))]
    def apply_tail():
        for row in suffix:
            result=incremental.run(destination/'child',KEY,row['request_id'],row['kind'],json.loads(row['args_json']))
            if result!=json.loads(row['response_json']):raise ValueError('Identical-input child response changed')
    measure('apply_original_committed_tail',apply_tail)
    full=measure('full_history_validation',lambda:store.validate(normal_child,KEY))
    short=measure('immediate_parent_validation',lambda:incremental.validate(destination/'child',KEY))
    assert full['world_sha256']==short['world_sha256']
    exported=measure('incremental_export',lambda:incremental.export(destination/'child',destination/'portable',KEY))
    restored=measure('incremental_independent_restoration',lambda:incremental.restore(destination/'portable',destination/'restored',KEY))
    assert exported==restored==short
    assert source=={name:file_sha256(normal_child/name) for name in source}
    if suffix:
        row=suffix[-1];before=file_sha256(destination/'child/child/database.sqlite')
        assert incremental.run(destination/'child',KEY,row['request_id'],row['kind'],json.loads(row['args_json']))==json.loads(row['response_json'])
        assert before==file_sha256(destination/'child/child/database.sqlite')
    sizes={name:sum(p.stat().st_size for p in (destination/name).rglob('*') if p.is_file()) for name in ('sealed','portable')}
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','timings':timings,'parent_operations':parent['operations'],'suffix_operations':len(suffix),
            'identical_world_sha256':short['world_sha256'],'source_unchanged':True,'exact_response_replay':True,
            'independent_suffix_replay':True,'independent_restoration':True,'parent_full_replay_attested':True,
            'verification_wall_reduction_percent':100*(1-timings['immediate_parent_validation']['wall_seconds']/timings['full_history_validation']['wall_seconds']),
            'verification_cpu_reduction_percent':100*(1-timings['immediate_parent_validation']['cpu_seconds']/timings['full_history_validation']['cpu_seconds']),
            'sizes_bytes':sizes,'process_peak_rss_bytes':peak_memory(),'production_modified':False,
            'limitations':'Single paired sample; source and child state identical. Initial full parent sealing cost is separate. New profile trusts a signed full-parent attestation, not fresh ancestor simulation on every restore. Not an episode latency benchmark or an official-capable profile.'}
    (destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent-package',type=Path,required=True);p.add_argument('--child',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.parent_package,a.child,a.output),indent=2))
