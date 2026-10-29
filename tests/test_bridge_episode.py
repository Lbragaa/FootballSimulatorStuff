"""Episode fault/replay/chronology tests; no production paths or football draws."""
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from braga_era.bridge.episode import Episode, projection
from braga_era.bridge.automatic import Automatic
from braga_era.history import canonical_json, digest
from test_bridge_control import controls
from test_bridge_worker2 import req


@pytest.fixture
def world(controls, tmp_path, monkeypatch):
    auto = Automatic(controls, tmp_path / 'automatic')
    auto.initialize()
    auto.set_mode(True, req(auto.career, 'enable_automatic_gameplay', 1, confirmation='ENABLE_AUTOMATIC_GAMEPLAY'), 1)
    episode = Episode(auto)
    fixtures = [dict(key=f'league:{i}',competition='LEAGUE',stage='R27',kickoff=f'2027-10-{9+i:02} 16:00',
                     status='scheduled',home='club:15' if i==3 else 'club:2',away='club:3') for i in range(1,5)]
    s = {'fixtures':fixtures,'ties':[],'draws':[],'names':{},'revealed':[]}
    head = ['a'*64]; cursors={}; batches=[]; pages={}
    monkeypatch.setattr(auto.career,'identity',lambda:{'checkpoint':head[0], 'career':'task04c-test','test_only':True})
    monkeypatch.setattr(auto.career,'inspect',lambda:{'accepted_clock':'2027-10-09 17:33'})
    def nexts(*args,**kwargs):
        if args[0]=='table':
            return {'standings':[dict(id=i,name=str(i),gf=1,ga=0,points=3,played=1,wins=1,draws=0,losses=0) for i in range(20)]}
        waiting=[f for f in fixtures if f['status']=='final' and f['key'] not in s['revealed']]
        scheduled=[f for f in fixtures if f['status']!='final']
        rows=waiting[:1] or scheduled[:1]
        return {'events':[{**f,'kind':'narration' if waiting else 'match'} for f in rows]}
    monkeypatch.setattr(auto.career,'play',nexts)
    monkeypatch.setattr(episode,'state',lambda:deepcopy(s))
    monkeypatch.setattr(auto.career,'preview',lambda k:{'fixture_key':k,'home':'Vasco','away':'Other','lineups':[],'kickoff':'2027-10-12 16:00'})
    def play(request):
        saved=next((b for b in batches if b==request['request_id']),None)
        if not saved:
            f=next(f for f in fixtures if f['status']=='scheduled')
            f['status']='final'; batches.append(request['request_id']); head[0]=digest(batches)
        return {'accepted_checkpoint':head[0]}
    monkeypatch.setattr(auto,'play',play)
    monkeypatch.setattr(auto,'resumable',lambda r:r['request_id'] in batches)
    def page(fixture,pid):
        if pid in pages: return pages[pid]
        pos=cursors.get(fixture,0)
        events=[[{'sequence':1,'kind':'KICKOFF'},{'sequence':2,'kind':'GOAL','details':{'score':[1,0]}},
                 {'sequence':3,'kind':'HALF_TIME'}],
                [{'sequence':4,'kind':'SECOND_HALF_KICKOFF'},{'sequence':5,'kind':'FINAL_WHISTLE'}]][pos]
        cursors[fixture]=pos+1
        done=pos==1
        if done:s['revealed'].append(fixture)
        p={'events':events,'postmatch_available':done,'postmatch_summary':{'score':[1,0],'resolution':{}}}
        pages[pid]=deepcopy(p)
        return p
    monkeypatch.setattr(episode,'_page',page)
    monkeypatch.setattr(episode,'final_stats',lambda f,s:s)
    monkeypatch.setattr(episode,'results_sections',lambda op,budget:([],[]))
    return SimpleNamespace(ep=episode,auto=auto,s=s,batches=batches,head=head,pages=pages,cursors=cursors,fixtures=fixtures)


def request(world): return req(world.auto.career,'play_next_episode',2)


def test_one_request_multiple_dates_full_match_and_round(world):
    r=request(world); v=world.ep.run(r)
    assert len(world.batches)==4
    assert v['episode_type']=='vasco_match'
    sections=v['presentation']
    events=[e for s in sections for e in s.get('events',[])]
    assert [e['kind'] for e in events]==['KICKOFF','GOAL','HALF_TIME','SECOND_HALF_KICKOFF','FINAL_WHISTLE']
    assert all('score' not in e['details'] for e in events)
    assert next(i for i,s in enumerate(sections) if s['section']=='fulltime')>max(i for i,s in enumerate(sections) if s['section']=='vasco_timeline')
    table=next(s for s in sections if s['section']=='league_table')
    assert table['complete'] and len(table['data'])==20
    assert not any(s['section']=='roundup' for s in sections)
    assert world.ep.run(r)==v and len(world.batches)==4
    assert len(canonical_json(v).encode())<48000


@pytest.mark.parametrize('fault',['after_acceptance','after_page','after_step','before_response'])
def test_crash_same_request_recovers_no_duplicate_effects(world,fault):
    r=request(world)
    world.ep.crash=fault
    with pytest.raises(RuntimeError): world.ep.run(r)
    assert world.ep.resumable(r)
    world.ep.crash=None
    result=world.ep.run(r)
    assert len(world.batches)==4==len(set(world.batches))
    assert len(world.pages)==8
    assert len(world.s['revealed'])==4
    assert world.ep.run(r)==result


def test_milestone_only_after_all_legs_and_not_repeated(world):
    for f in world.fixtures:
        f.update(competition='LIB',stage='QF',home='club:2',tie_key='lib:QF-01',leg=2,
                 home_goals=1,away_goals=0,resolution_json='{}')
    world.s['ties']=[dict(key='lib:QF-01',competition='LIB',stage='QF',status='scheduled',
                         winner=None,club_a='club:2',club_b='club:3',aggregate_a=4,aggregate_b=0)]
    original=world.auto.play
    def advance(r):
        result=original(r)
        if len(world.batches)==4:world.s['ties'][0].update(status='final',winner='club:2')
        return result
    world.auto.play=advance
    v=world.ep.run(request(world))
    assert v['episode_type']=='competition_milestone'
    report=next(s['data'] for s in v['presentation'] if s['section']=='milestone_report')
    assert report['ties'][0]['aggregate']==[4,0]
    assert len(report['ties'][0]['legs'])==4
    v2=world.ep.run(req(world.auto.career,'play_next_episode',3))
    assert v2['episode_type']=='season_complete'
    assert not any(s['section']=='milestone_report' for s in v2['presentation'])


def test_revocation_and_calendar_bound(world,monkeypatch):
    world.auto.set_mode(False,req(world.auto.career,'disable_automatic_gameplay',3),2)
    assert world.ep.run(request(world))['episode_type']=='automatic_disabled'
    assert not world.batches
    world.auto.set_mode(True,req(world.auto.career,'enable_automatic_gameplay',4,confirmation='ENABLE_AUTOMATIC_GAMEPLAY'),3)
    monkeypatch.setattr('braga_era.bridge.episode.MAX_BATCHES',1)
    assert world.ep.run(req(world.auto.career,'play_next_episode',5))['episode_type']=='progress_bound'
    assert len(world.batches)==1


def test_order_survives_wire_serialization_and_no_preview_result(world):
    v=json.loads(canonical_json(world.ep.run(request(world))))
    sections=v['presentation']
    assert sections[0]['section']=='prematch'
    assert 'score' not in canonical_json(sections[0])
    assert all(s['section'] not in {'fulltime','league_table'} for s in sections[:2])


def test_partial_round_never_claimed_final_or_cross_second_vasco(world):
    world.fixtures[-1]['home']='club:15'
    result=world.ep.run(request(world))
    assert len(world.batches)==3
    assert not any(s['section']=='league_table' for s in result['presentation'])
    assert any(s['section']=='round_pending' for s in result['presentation'])


def test_genuine_uncommitted_dependency_fails_closed(world):
    def blocked(r): raise ValueError('private diagnostic path must never leak')
    world.auto.play=blocked
    result=world.ep.run(request(world))
    assert result['episode_type']=='blocker' and not world.batches
    assert 'private diagnostic' not in canonical_json(result)


def test_projection_removes_duplicate_field_arrays():
    value=projection({'sequence':2,'kind':'GOAL','on_field_home':[1,2],'on_field_away':[3],
                      'details':{'assister_id':5,'score':[1,0]}})
    assert 'on_field_home' not in value and value['details']=={'assister_id':5}


def test_first_response_normalizes_integer_mapping_keys(world,monkeypatch):
    monkeypatch.setattr(world.auto.career,'preview',lambda f:{'fixture_key':f,'lineups':[{'roles':{123:'captain'}}]})
    r=request(world); first=world.ep.run(r)
    assert first==world.ep.run(r)
    world.head[0]='f'*64  # old delivery survives later unrelated accepted heads.
    assert first==world.ep.run(r)


def test_mathematical_league_milestones_respect_recorded_rule(world):
    rows=[dict(id=i,points=40,played=37) for i in range(20)]
    rows[0]['points']=90
    rows[-1]['points']=0
    result=world.ep.league_outcomes({'league':rows})
    assert 'title:club:0' in result and 'relegation:club:19' in result
    assert not any('qualification' in x for x in result)


def test_issue_round_trip_crash_and_same_final_response(world,tmp_path):
    from braga_era.bridge.worker2 import Worker2
    from test_bridge import Transport
    from test_bridge_worker2 import users
    t=Transport()
    w=Worker2(t,world.auto.career,tmp_path/'worker'/'ledger.sqlite',users(),controls=world.auto.controls,automatic=world.auto)
    w.episodes=world.ep
    r=request(world); r['sequence']=1
    issue=t.add(r)
    w.crash='after_response_before_post'
    with pytest.raises(RuntimeError):w.poll()
    w.crash=None
    w.poll()
    first=t.result(issue)
    assert first['response']['status']=='completed'
    assert first['response']['result']['episode_type']=='vasco_match'
    duplicate=t.add(r)
    w.poll()
    assert t.result(duplicate)==first and len(world.batches)==4


def test_interrupted_vasco_resumes_without_replaying_goal(world):
    for f in world.fixtures[:3]: f['status']='final'
    world.s['revealed']=[f['key'] for f in world.fixtures[:2]]
    world.cursors[world.fixtures[2]['key']]=1
    result=world.ep.run(request(world))
    events=[e for s in result['presentation'] for e in s.get('events',[])]
    assert [e['sequence'] for e in events]==[4,5]
    assert len(world.batches)==1


def test_committed_dependency_adopts_original_child_without_replacement(world):
    original=world.auto.play
    attempts=[]
    def blocked(r):
        attempts.append(r['request_id'])
        if len(attempts)==1:
            world.auto._save(world.auto._path(r),{'retained_commitment':True})
            raise ValueError('Unresolved qualifier/draw at 2027-10-10 16:00')
        return original(r)
    world.auto.play=blocked
    r=request(world)
    assert world.ep.run(r)['episode_type']=='blocker'
    second=world.ep.run(req(world.auto.career,'play_next_episode',3))
    assert attempts[0]==attempts[1]  # original exact request/seed commitment.
    assert second['episode_type']=='vasco_match' and len(world.batches)==4
    assert world.ep.run(r)['episode_type']=='blocker'  # old response is immutable.
    assert world.auto._read(world.ep.path(r))['pending'] is None


def test_time_bound_returns_resumable_progress(world,monkeypatch):
    monkeypatch.setattr('braga_era.bridge.episode.MAX_SECONDS',0)
    result=world.ep.run(request(world))
    assert result['episode_type']=='progress_bound' and result['recovery']['resumable']
    assert not world.batches


def test_bounded_continuation_finishes_same_round_not_next_vasco(world,monkeypatch):
    monkeypatch.setattr('braga_era.bridge.episode.MAX_PAGES',7)
    first=world.ep.run(request(world))
    assert first['episode_type']=='progress_bound'
    assert any(s['section']=='fulltime' for s in first['presentation'])
    monkeypatch.setattr('braga_era.bridge.episode.MAX_PAGES',256)
    result=world.ep.run(req(world.auto.career,'play_next_episode',3))
    assert result['episode_type']=='vasco_match'
    assert any(s['section']=='league_table' for s in result['presentation'])
    assert not any(s['section']=='vasco_timeline' for s in result['presentation'])
