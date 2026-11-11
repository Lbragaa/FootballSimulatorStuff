from collections import Counter
from contextlib import closing
from dataclasses import asdict, replace
import json
import sqlite3

import pytest

from braga_era.engine import commit_seeds, prepare, simulate_match, validate_match
from braga_era.engine.config import REALISM_VERSION
from braga_era.engine.match import prematch
from braga_era.history import canonical_json
from braga_era.multiseason import development as dev, market, offseason
from braga_era.multiseason.schema import DDL
from braga_era.world.forward_config import configuration, load
from braga_era.world.knockout_v2 import resolve, validate_bundle
from braga_era.world.policy import ReadinessPolicy, Rules
from braga_era.world.schema import DDL as WORLD
from test_substitution_policy import fixture


def test_candidate_dismissals_and_extra_time_are_coherent():
    policy = ReadinessPolicy()
    config = configuration(policy, engine_version=REALISM_VERSION)
    assert load(asdict(config), policy) == config
    snapshot = fixture()
    totals = {'reds': 0, 'seconds': 0, 'extra_time': 0}
    for index in range(80):
        seeds = commit_seeds(snapshot, config, f'realism-invariant:{index}')
        plans = prepare(snapshot, config, seeds)
        result = simulate_match(snapshot, plans, config, seeds)
        validate_match(snapshot, result, config)
        rules = Rules('STATE', extra_time=True, penalties=True)
        bundle = resolve(snapshot, result, config, rules)
        validate_bundle(snapshot, result, config, rules, (0, 0), bundle)
        red = set()
        yellow = Counter()
        previous = None
        for event in bundle['events']:
            kind, player = event['kind'], event['player_id']
            if kind in {'YELLOW_CARD', 'RED_CARD', 'SHOT'}:
                assert player not in red
            if kind == 'YELLOW_CARD':
                yellow[player] += 1
            if kind == 'RED_CARD':
                if event['details']['reason'] == 'second yellow':
                    assert yellow[player] == 2
                    assert (previous['kind'], previous['player_id']) == ('YELLOW_CARD', player)
                    totals['seconds'] += 1
                red.add(player)
            previous = event
        totals['reds'] += len(red)
        totals['extra_time'] += int(bundle['duration_seconds'] > result.duration_seconds)
        if index == 0:
            assert simulate_match(snapshot, plans, config, seeds).fingerprint == result.fingerprint
    assert all(totals.values())


def test_age_role_potential_and_no_form_drift():
    attrs = asdict(fixture().home.players[2])
    career = dev.profile(attrs, dev.stream('career', 2), hint=87)
    young, older = [], []
    for n in range(90):
        y = dev.project(attrs, 19, career, 150000, 0, dev.stream('career', n, 'test'))
        v = dev.project(attrs, 38, career, 150000, 0, dev.stream('career', n, 'test'))
        young.append(y['ovr']-attrs['ovr'])
        older.append(v['ovr']-attrs['ovr'])
        assert y['goalkeeping']==attrs['goalkeeping'] and y['fitness']==attrs['fitness']
        assert abs(y['ovr'] - dev.rating(y) - career['ovr_offset']) < .001
        assert max(abs(v[k]-attrs[k]) for k in dev.WEIGHTS[attrs['position']]) <= 2.701
    assert sum(young)>0 and sum(older)<0 and max(older)<0
    assert sum(delta>0 for delta in young) > 60


def test_persisted_development_reuses_trajectory_after_transfer():
    with closing(sqlite3.connect(':memory:')) as c:
        c.row_factory=sqlite3.Row
        c.executescript(WORLD+DDL+offseason.DDL)
        c.execute("INSERT INTO ms_meta VALUES(1,'test','p','h','{}','fixed','2028-06-28 17:33:00',1)")
        attrs=asdict(fixture().home.players[2])
        pid=attrs['id']
        c.execute("INSERT INTO world_players VALUES(?,?,NULL,1,?,'{}')",(pid,'first',canonical_json(attrs)))
        start='2028-06-28 17:33:00'
        c.execute("INSERT INTO ms_seasons VALUES(2029,'preparing',NULL)")
        c.execute('INSERT INTO ms_operations VALUES(1,?,?,?,?,?,?,?)',
                  ('activate',dev.ACTIVATION,'{}',canonical_json({'effective_after':start}),'p','h','s'))
        c.execute("INSERT INTO ms_editions VALUES('STATE:2028','STATE',2028,'league','{}','active',NULL)")
        for match_id, kickoff, seconds in [('old','2028-06-01 16:00',3600),('new','2028-07-10 16:00',1800)]:
            c.execute("""INSERT INTO ms_fixtures VALUES(?,'STATE:2028','LEAGUE',1,NULL,?,
                      'second',?,'final',1,0,NULL)""",(match_id,match_id,kickoff))
            result=canonical_json({'performances':[{'player_id':pid,'seconds_played':seconds,'injured':False}]})
            c.execute('INSERT INTO ms_executions VALUES(?,?,?,?,?,?,?)',(match_id,'{}','h','{}','{}',result,'h'))
        assert market.apply(c,'evolve',{'season':2029})['players_evolved']==1
        one=c.execute('SELECT * FROM ms_attributes').fetchone()
        assert json.loads(one['before_json'])==json.loads(canonical_json(attrs))
        current=json.loads(one['after_json'])
        assert current['ovr']!=attrs['ovr']
        c.commit()
        with pytest.raises(ValueError,match='already consumed'), c:
            market.apply(c,'evolve',{'season':2029})
        current['club_key']='second'
        c.execute('UPDATE world_players SET club_key=?,attributes_json=? WHERE id=?',
                  ('second',canonical_json(current),pid))
        prior = json.loads(one['assumption_json'])
        provenance = 'explicit modeled age prior; no historical birthdate asserted'
        c.execute("INSERT INTO ms_lifecycle VALUES(?,?,2029,'active',?)",
                  (pid,prior['age'],canonical_json({'age':provenance})))
        c.execute("INSERT INTO world_clubs VALUES('second','Second','second',NULL,'BRA',70,6.5,'{}')")
        assert offseason.evolve(c,2030,'2030-01-01',{'second'}) == {
            'developed':1,'retired':0,'youth':2,
        }
        new=c.execute('SELECT * FROM ms_attributes WHERE season=2030').fetchone()
        a,b=(json.loads(r['assumption_json']) for r in (one,new))
        assert a['trajectory']==b['trajectory'] and b['age']==a['age']+1
        assert b['age_basis']==provenance
        assert a['seconds']==1800
        assert json.loads(new['after_json'])['club_key']=='second'
        assert a['annual_fraction']<1 and b['annual_fraction']==1


def test_developed_forward_can_win_selection_and_raise_xg():
    snap=fixture()
    conf=configuration(ReadinessPolicy(),engine_version=REALISM_VERSION)
    reserve = max(p.id for p in snap.home.players if p.position=='FW')
    base=replace(snap.home,coach=replace(snap.home.coach,decision_noise=0),
                 players=tuple(replace(p,ovr=71 if p.id==reserve else 72,fitness=98)
                               if p.position=='FW' else p for p in snap.home.players))
    snap=replace(snap,home=base)
    original_plans=prepare(snap,conf,commit_seeds(snap,conf,'development-selection'))
    original=prematch(snap,original_plans,conf)
    candidate=next(p for p in base.players if p.id==reserve)
    assert reserve not in original_plans[0].starters
    attrs=asdict(candidate)
    career=dev.profile(attrs,dev.stream('selection',candidate.id),hint=96)
    for age in range(16,26):
        attrs=dev.project(attrs,age,career,126000,0,dev.stream('selection',candidate.id,age))
    improved=replace(snap,home=replace(base,players=tuple(replace(p,**attrs) if p.id==candidate.id else p
                                                          for p in base.players)))
    plans=prepare(improved,conf,commit_seeds(improved,conf,'development-selection'))
    assert candidate.id in plans[0].starters
    assert prematch(improved,plans,conf).expected_xg[0]>original.expected_xg[0]
