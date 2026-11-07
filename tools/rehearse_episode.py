"""Disconnected NONCANONICAL clone of an actual accepted career for episode QA.

No transport/credential is constructed. Original signed history/mode is retained
in a private clone, so it still identifies its original career (not a relabeled
TEST authority). New clone results are NEVER published or copied back. The key
is read into memory only, never duplicated into the rehearsal or its report.
"""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era import lineage
from braga_era.bridge.__main__ import config, build
from braga_era.bridge.approval import HumanGate
from braga_era.bridge.career import Career
from braga_era.bridge.control import Controls
from braga_era.bridge.automatic import Automatic
from braga_era.bridge.episode import Episode
from braga_era.db import file_sha256
from braga_era.history import canonical_json as encode
from braga_era.world.storage import process_lock


def clone(source_config, target, resume=False):
    spec = config(source_config)
    source = Path(source_config).resolve().parent
    target = Path(target).resolve()
    if source == target or source in target.parents or target.exists() and not resume:
        raise ValueError('Use a fresh separate private rehearsal directory')
    if resume and not (target/'REHEARSAL.json').is_file():
        raise ValueError('Resume requires an existing disconnected rehearsal marker')
    target.mkdir(parents=True, exist_ok=resume)
    original = build(spec, '')
    key = original.career.key  # memory only; no GitHub call, token or key copy.
    baseline = original.career.inspect()
    if not resume:
      with process_lock(Path(spec['ledger']).parent, name='.bridge-worker.lock'):
        with sqlite3.connect(spec['registry']) as src, sqlite3.connect(target/'authority.sqlite') as dst:
            src.backup(dst)
        baseline = original.career.inspect()
    if not resume:
      with sqlite3.connect(target/'authority.sqlite') as db:
        rows = db.execute('SELECT checkpoint,path FROM accepted ORDER BY generation').fetchall()
        mapping = {}
        for checkpoint, path in rows:
            out = target/'accepted'/checkpoint
            shutil.copytree(path, out)
            mapping[str(Path(path))] = str(out)
            db.execute('UPDATE accepted SET path=? WHERE checkpoint=?', (str(out), checkpoint))
        for batch, directory, parent in db.execute('SELECT id,directory,parent_path FROM batches').fetchall():
            db.execute('UPDATE batches SET directory=?,parent_path=? WHERE id=?',
                       (mapping.get(str(Path(directory)), str(target/'unused'/batch)) if directory else None,
                        mapping.get(str(Path(parent)), str(target/'root.sqlite')), batch))
    if not resume: shutil.copyfile(spec['root_parent'], target/'root.sqlite')
    career = Career(target/'authority.sqlite', key, spec['career'], spec['test_only'])
    career.root_parent = target/'root.sqlite'
    gate = HumanGate(target/'gate.sqlite', key, b'DISCONNECTED-REHEARSAL-ONLY',
                     {k:v for k,v in original.controls.gate.context.items() if k!='authenticator_sha256'})
    if not resume:
        gate.initialize()
        shutil.copyfile(spec['control']['policy_receipt'], target/'policy.json')
    controls = Controls(career, target/'control.sqlite', target/'new-checkpoints', target/'policy.json', gate,
                        enabled=True, production_binding_approved=True)
    if not resume: controls.initialize()
    auto = Automatic(controls, target/'automatic')
    auto.directory.mkdir(exist_ok=resume)
    if not resume: shutil.copyfile(Path(spec['automatic_directory'])/'mode.json', auto.directory/'mode.json')
    focus = Path(spec['automatic_directory'])/'focus.json'
    if focus.exists() and not resume: shutil.copyfile(focus, auto.directory/'focus.json')
    marker = {'scope':'NONCANONICAL DISCONNECTED REHEARSAL - NEVER PROMOTE', 'source_checkpoint':baseline['accepted_checkpoint'],
              'source_registry_sha256':file_sha256(Path(spec['registry'])), 'no_network':True, 'no_key_copy':True}
    if not (target/'REHEARSAL.json').exists(): (target/'REHEARSAL.json').write_text(encode(marker),encoding='utf-8')
    return Episode(auto), original, baseline


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--episodes',type=int,default=1)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--crash-after-acceptance',action='store_true')
    a=p.parse_args()
    episode, original, baseline = clone(a.config,a.output,a.resume)
    rows=[]
    existing=sorted(episode.directory.glob('*.json'),key=lambda p:p.stat().st_mtime) if a.resume else []
    for i in range(a.episodes):
        request={'protocol':'braga-bridge-2','request_id':str(uuid4()),'sequence':i+1,
                 'career':episode.career.career,'expected_checkpoint':episode.career.identity()['checkpoint'],
                 'command':'play_next_episode','args':{}}
        if i<len(existing):
            old=episode.auto._read(existing[i])
            request=old.get('request') or {**request,'request_id':existing[i].stem,
                                          'expected_checkpoint':baseline['accepted_checkpoint']}
        start=time.perf_counter()
        if a.crash_after_acceptance and i==0:
            episode.crash='after_acceptance'
            try:
                episode.run(request)
            except RuntimeError as error:
                if str(error)!='Injected episode crash: after_acceptance':raise
            else:raise AssertionError('Expected crash did not occur')
            assert episode.resumable(request)
            episode.crash=None
        result=episode.run(request)
        wall=time.perf_counter()-start
        repeated=time.perf_counter()
        assert episode.run(request)==result
        repeat_seconds=time.perf_counter()-repeated
        journal=episode.auto._read(episode.path(request))
        state=episode.state()
        covered=[f for f in state['fixtures'] if f['key'] in journal['consumed']]
        groups={f['kickoff'] for f in covered}
        split_groups=sum(any(f['key']==journal['target'] for f in covered if f['kickoff']==g)
                         and sum(f['kickoff']==g for f in covered)>1 for g in groups)
        rows.append({'episode_type':result['episode_type'],'call_wall_seconds':round(wall,3),
                     'cached_repeat_seconds':round(repeat_seconds,3),
                     'crash_after_acceptance_recovered':a.crash_after_acceptance and i==0,
                     'response_bytes':len(encode(result).encode()), 'world_progress':result['world_progress'],
                     'timings_seconds':result['timings_seconds'], 'signed_pages':journal['pages'],
                     'new_transport_issues':1,'new_transport_replies':1,
                     'legacy_requests_lower_bound':journal['batches']+len(groups)+split_groups,
                     'legacy_basis':'one advance per day + one request per earliest narration group; split held Vasco/other summaries; excludes previews and additional size-limited delivery calls',
                     'sections':[s['section'] for s in result['presentation']]})
        (a.output/f'PRIVATE-NONCANONICAL-episode-{i+1}.json').write_text(encode(result),encoding='utf-8')
        print(encode(rows[-1]),flush=True)
        if result['episode_type'] in {'blocker','progress_bound','automatic_disabled','season_complete'}:break
    assert original.career.inspect()==baseline, 'Official career moved during rehearsal; investigate separately'
    with lineage.access(episode.career.registry,episode.career.key) as (c,t):
        assert c.execute('SELECT count(*) FROM batches WHERE state!=?',('accepted',)).fetchone()[0]==0
    report={'scope':'NONCANONICAL DISCONNECTED REHEARSAL','official_state_unchanged':True,
            'source_checkpoint':baseline['accepted_checkpoint'],'episodes':rows}
    (a.output/'benchmark.json').write_text(encode(report),encoding='utf-8')


if __name__=='__main__':main()
