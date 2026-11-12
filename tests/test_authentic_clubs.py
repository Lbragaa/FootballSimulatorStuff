from collections import Counter
from contextlib import closing
from itertools import groupby
import json
import sqlite3

import pytest

from braga_era.multiseason import authentic, continental_entry, offseason
from braga_era.multiseason.club_catalogue import entries
from braga_era.multiseason.schema import DDL
from braga_era.seasons import double_round_robin
from braga_era.world.rosters import alias
from braga_era.world.schema import DDL as WORLD


@pytest.mark.parametrize('n', [4, 8, 20, 32])
def test_balanced_venues_preserve_opponents(n):
    teams = [f'club:{i}' for i in range(n)]
    kwargs = dict(season=2029, competition='LEAGUE')
    old = double_round_robin(teams, **kwargs)
    balanced = double_round_robin(teams, policy=authentic.SCHEDULE, **kwargs)
    assert balanced == double_round_robin(teams[::-1], policy=authentic.SCHEDULE, **kwargs)
    assert len(balanced) == n*(n-1)
    assert {(r['home'], r['away']) for r in balanced} == {(r['home'], r['away']) for r in old}
    for club in teams:
        homes = [r['home'] == club for r in balanced if club in (r['home'], r['away'])]
        assert Counter(homes) == {True: n-1, False: n-1}
        assert max(len(list(run)) for _, run in groupby(homes)) <= 3


def make_world(*, test_only=True):
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    schema = DDL if test_only else DDL.replace('CHECK(test_only=1)', 'CHECK(test_only IN (0,1))')
    c.executescript(WORLD+schema+offseason.DDL+'''CREATE TABLE league_participants(season,club_id);
        INSERT INTO ms_meta VALUES(1,'test','p','h','{}','fixed','2028-12-31 23:59:00',1);
        INSERT INTO ms_seasons VALUES(2028,'archived',NULL),(2029,'preparing',NULL);
        INSERT INTO world_clubs VALUES('legacy-est','Estudiantes','estudiantes',NULL,'ARG',76,0,'{}'),
         ('legacy-ldu','LDU Quito','ldu quito',NULL,NULL,74,0,'{}'),
         ('legacy-fic','Fictional Initial Access Entrant 007','fictional initial access entrant 007',NULL,'BRA',70,0,'{}');''')
    return c


def test_install_preserves_recorded_identities_and_names_future_players():
    args = {'season': 2029, 'policy': authentic.POLICY}
    with closing(make_world()) as c, closing(make_world()) as replica:
        old = [tuple(r) for r in c.execute('SELECT * FROM world_clubs')]
        legacy = '{"name":"Fictional LDU Quito FW-23"}'
        for world in (c, replica):
            world.execute("INSERT INTO world_players VALUES(7,'legacy-ldu',NULL,1,?,'{}')",(legacy,))
            world.execute("INSERT INTO world_players VALUES(8,'legacy-ldu',8,0,'{\"name\":\"Recorded Player\"}','{}')")
        assert authentic.install(c, args) == authentic.install(replica, args)
        clubs = authentic.catalogue(c, 2029)
        assert len(clubs) == len(list(entries()))
        assert 'legacy-fic' not in clubs
        assert clubs['legacy-est']['name'] == 'Estudiantes de La Plata'
        assert continental_entry.country_of(c, 'legacy-ldu') == 'ECU'
        assert continental_entry.country_of(c, 'legacy-fic') == 'BRA'
        for row in old:
            assert row == tuple(c.execute('SELECT * FROM world_clubs WHERE key=?',(row[0],)).fetchone())
        squads = {}
        diversity = set()
        for row in c.execute('SELECT * FROM world_players ORDER BY id'):
            twin = replica.execute('SELECT attributes_json FROM world_players WHERE id=?',(row['id'],)).fetchone()
            assert twin[0] == row['attributes_json']
            if row['id'] in (7,8):
                continue
            p = json.loads(row['attributes_json'])
            assert all(char.isalpha() or char in ' -’' for char in p['name'])
            assert 'Fictional' not in p['name'] and len(p['name'].split()) >= 2
            names = squads.setdefault(row['club_key'], set())
            assert p['name'] not in names
            names.add(p['name'])
            origin = json.loads(row['provenance_json'])
            diversity.add(origin['nationality'])
        assert len(diversity) == 10
        assert authentic.display_names(c,2028) == {}
        assert authentic.display_names(c,2029)['7']['original'] == 'Fictional LDU Quito FW-23'
        assert '8' not in authentic.display_names(c,2029)
        assert c.execute('SELECT attributes_json FROM world_players WHERE id=7').fetchone()[0] == legacy
        assert min(map(len,squads.values())) >= 24
        assert max(map(len,squads.values())) <= 28
        assert max(r['prior'] for r in clubs.values()) - min(r['prior'] for r in clubs.values()) >= 20
        for country in continental_entry.ALLOCATIONS:
            if country=='BRA':
                continue
            ranking = continental_entry.ranking(c,country,2029,{'type':'authentic_national_model'})
            assert ranking == authentic.order(replica,country,2029)
            assert len(ranking) > continental_entry.ALLOCATIONS[country]+continental_entry.SULA_SLOTS[country]
        rio = next(k for k,v in clubs.items() if v['state']=='RJ' and k in squads)
        pid = offseason.youth(c,rio,2029,1,'FW','2029-01-01',65)
        attrs = json.loads(c.execute('SELECT attributes_json FROM world_players WHERE id=?',(pid,)).fetchone()[0])
        assert attrs['name'] not in squads[rio]
        assert 'academy' not in attrs['name']
        with pytest.raises(ValueError,match='new catalogue'):
            authentic.install(c,args)
        assert authentic.opening_liquidity_allowed(c,rio,2029)
        assert not authentic.opening_liquidity_allowed(c,rio,2030)
        assert not authentic.opening_liquidity_allowed(c,'legacy-est',2029)
        initial = authentic.display_names(c,2029)['7']
        count = c.execute('SELECT count(*) FROM world_clubs').fetchone()[0]
        c.execute("UPDATE ms_seasons SET state='archived' WHERE season=2029")
        c.execute("INSERT INTO ms_seasons VALUES(2030,'preparing',NULL)")
        assert authentic.install(c,{**args,'season':2030})['new_clubs'] == 0
        assert c.execute('SELECT count(*) FROM world_clubs').fetchone()[0] == count
        assert authentic.display_names(c,2030)['7'] == initial


def test_vacancy_has_distinct_identity_and_keeps_sporting_provenance():
    with closing(make_world()) as c:
        authentic.install(c,{'season':2029,'policy':authentic.POLICY})
        existing = next(k for k,v in authentic.catalogue(c,2029).items() if v['state']=='SP')
        original = {'type':'edition_position','edition':'SERIE_B:2028','position':1}
        routes = {'LEAGUE': [('legacy-fic', original)], 'SERIE_B': [(existing, {})]}
        authentic.division_replacements(c,2029,routes)
        replacement,source = routes['LEAGUE'][0]
        assert replacement.startswith('real:') and replacement!=existing
        assert source['vacated_club']=='legacy-fic' and source['sporting_source']==original
        assert c.execute("SELECT name FROM world_clubs WHERE key='legacy-fic'").fetchone()[0].startswith('Fictional')


def test_catalogue_refuses_production():
    with closing(make_world(test_only=False)) as c:
        c.execute('UPDATE ms_meta SET test_only=0')
        with pytest.raises(ValueError, match='future TEST preseason'):
            authentic.install(c,{'season':2029,'policy':authentic.POLICY})


def test_schedule_has_independent_precommit_gate():
    with closing(make_world()) as c:
        args = {'season': 2029, 'policy': authentic.SCHEDULE}
        assert authentic.commit_schedule(c, args)['policy'] == authentic.SCHEDULE
        assert not authentic.catalogue(c, 2029)
        with pytest.raises(ValueError, match='uncommitted'):
            authentic.commit_schedule(c, args)
        c.execute("INSERT INTO ms_seasons VALUES(2030,'preparing',NULL)")
        c.execute("INSERT INTO ms_editions VALUES('LEAGUE:2030','LEAGUE',2030,'league','{}','active',NULL)")
        c.execute("""INSERT INTO ms_fixtures VALUES('r1','LEAGUE:2030','LEAGUE',1,NULL,
            'legacy-est','legacy-fic','2030-02-01 16:00','scheduled',NULL,NULL,NULL)""")
        with pytest.raises(ValueError, match='uncommitted'):
            authentic.commit_schedule(c, {**args, 'season': 2030})
