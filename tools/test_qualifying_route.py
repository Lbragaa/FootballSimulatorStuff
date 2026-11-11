"""Disposable route and signed delivery recovery for the qualifying import."""
from pathlib import Path
import sys
from uuid import uuid4

from braga_era.bridge.__main__ import build, config
from braga_era import lineage
from braga_era.db import file_sha256


def run(root, worker, head, first_vasco):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
    from test_bridge import Transport
    transport=Transport()
    worker.transport=transport
    body={'protocol':'braga-bridge-2','request_id':str(uuid4()),'sequence':1,
          'career':worker.career.career,'expected_checkpoint':head,'command':'play_next_episode','args':{}}
    stale=transport.add({**body,'career':'the-braga-era-alt-episode81','request_id':str(uuid4())})
    number=transport.add(body)
    with lineage.access(worker.career.registry,worker.career.key) as (c,t):
        from braga_era import season_lineage
        info,_=season_lineage.current(c,t,worker.career.key)
        database=info['database']
        baseline=file_sha256(database)
    transport.lost_post=True
    try:
        worker.poll()
    except RuntimeError as error:
        assert str(error)=='Network lost after successful POST'
    else:
        raise AssertionError('Interrupted delivery was not exercised')
    restarted=build(config(root/'config.json'),'')
    restarted.transport=transport
    restarted.poll()
    assert not transport.comments(stale) and len(transport.comments(number))==1
    result=transport.result(number)
    assert restarted.verify_response(result)
    result=result['response']['result']
    assert result['accepted_checkpoint']==head and result['world_progress']['batches']==0
    sections=result['presentation']
    timeline=[section for section in sections if section['section']=='vasco_timeline']
    assert timeline and {p['fixture'] for p in timeline}=={first_vasco}
    assert timeline[-1]['events'][-1]['kind']=='FINAL_WHISTLE'
    assert not any(p['section']=='league_table' for p in sections)
    assert file_sha256(database)==baseline
    print('Isolated bridge recovered the same first narration delivery after restart and ignored the stale career request.',flush=True)
