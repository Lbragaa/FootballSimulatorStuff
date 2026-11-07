"""Paired read-only audits of an identical accepted TEST successor.

The full baseline replays every multiseason operation since migration; rolling
replays exactly the immediate-parent suffix. Both compare every resulting table.
No cache verdict substitutes for file authentication or independent simulation.
"""
import argparse
import ctypes
import json
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
import time

from braga_era import lineage,season_lineage as seasons
from braga_era.history import digest
from tools.rehearse_registered_seasons import KEY


def snapshot(registry,destination):
    """Copy public-credential TEST evidence while the rehearsal keeps running.

    SQLite backup pins one accepted head. Already published chunks are immutable,
    so a simultaneous later acceptance cannot change any copied object.
    """
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Fresh owned benchmark directory required')
    with lineage.access(registry,KEY) as (c,t):
        if not t['test_only'] or t['seed']!='lineage-career-v1:season-boundary-test:season-boundary-fixed-v1':raise ValueError('Fixed public TEST rehearsal required')
        destination.mkdir(parents=True);target=destination/'authority/registry.sqlite';target.parent.mkdir()
        with closing(sqlite3.connect(target)) as copied:c.backup(copied)
        with lineage.access(target,KEY) as (copy,trust):
            accepted=copy.execute('SELECT checkpoint,path FROM accepted ORDER BY generation').fetchall()
            for index,row in enumerate(accepted):
                folder=destination/'accepted'/str(index);folder.parent.mkdir(exist_ok=True)
                source=Path(row['path'])
                if seasons.is_registered(source):shutil.copytree(source/'payload',folder/'payload')
                else:
                    shutil.copytree(source/'payload',folder/'payload');shutil.copyfile(source/'checkpoint.zip',folder/'checkpoint.zip')
                copy.execute('UPDATE accepted SET path=? WHERE checkpoint=?',(str(folder),row['checkpoint']))
            head=copy.execute('SELECT path,proof FROM accepted WHERE checkpoint=?',(trust['head'],)).fetchone()
            package=seasons.read_package(head['path'])
            # Read through the original pool only to discover signed references.
            token=seasons.POOL_OVERRIDE.set(seasons.pool(c))
            try:identities=seasons._reachable(copy,package,json.loads(head['proof']))
            finally:seasons.POOL_OVERRIDE.reset(token)
            objects=seasons.pool(copy);objects.mkdir()
            for identity in identities:shutil.copyfile(seasons.pool(c)/(identity+'.gz'),objects/(identity+'.gz'))
    return target


def peak_memory():
    if os.name=='nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD),
                      *[(name,ctypes.c_size_t) for name in ('peak','working','paged_peak','paged','nonpaged_peak','nonpaged','pagefile','pagefile_peak')]]
        value=Counters();value.cb=ctypes.sizeof(value)
        handle=ctypes.windll.kernel32.GetCurrentProcess
        handle.restype=wintypes.HANDLE
        measure=ctypes.windll.psapi.GetProcessMemoryInfo
        measure.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        measure.restype=wintypes.BOOL
        if not measure(handle(),ctypes.byref(value),value.cb):raise OSError('Memory measurement failed')
        return value.peak
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if os.uname().sysname=='Darwin' else 1024)


def run(registry,output,*,samples=3):
    if type(samples) is not int or not 1<=samples<=3:raise ValueError('One to three measured successors required')
    peak_memory()  # Check the measurement API before doing expensive replay.
    results=[]
    with lineage.access(registry,KEY) as (c,t):
        if not t['test_only']:raise ValueError('Public TEST signer and isolated registry required')
        rows=c.execute("SELECT path,proof FROM accepted ORDER BY generation DESC").fetchall()
        rows=[r for r in rows if json.loads(r['proof'])['metadata']['profile']==seasons.PROFILE][:samples]
        if len(rows)<samples:raise ValueError('Insufficient real accepted successors')
        for index,row in enumerate(reversed(rows)):
            target=Path(row['path']);package=seasons.read_package(target)
            # Authenticate an immutable accepted earlier parent, without ever
            # changing the actual registry head or accepting a competing child.
            view={**dict(t),'head':package['metadata']['immediate_parent_sha256']}
            item={'generation':package['metadata']['generation'],'checkpoint':digest(package['metadata']),
                  'database_bytes':package['state']['database.sqlite']['bytes'],
                  'logical_state_sha256':package['metadata']['world_sha256'],'measurements':{}}
            # Alternate order to disclose/reduce systematic filesystem warmup.
            for mode in (('full','rolling') if index%2==0 else ('rolling','full')):
                before=time.perf_counter();cpu=time.process_time()
                checked=seasons.verify_candidate(c,view,KEY,target,replay='full' if mode=='full' else True)
                if checked!=package:raise ValueError('Verification changed accepted bytes')
                item['measurements'][mode]={'wall_seconds':time.perf_counter()-before,'cpu_seconds':time.process_time()-cpu,
                                            'process_peak_memory_bytes':peak_memory()}
            item['wall_reduction_percent']=100*(1-item['measurements']['rolling']['wall_seconds']/item['measurements']['full']['wall_seconds'])
            results.append(item)
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','identical_inputs_and_results':True,'accepted_successors':results,
            'includes':'authentication, file reconstruction, structural/history checks, independent replay and all-table comparison',
            'excludes':'execution, acceptance and real GitHub polling; those are separately measured by the integrated runner',
            'memory_note':'cumulative process peak, not a per-phase isolated peak'}
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=3)
    a=p.parse_args();print(json.dumps(run(a.registry,a.output,samples=a.samples),indent=2))
