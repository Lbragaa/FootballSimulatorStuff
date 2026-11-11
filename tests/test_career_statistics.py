from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import sqlite3
from uuid import uuid4

import pytest

from braga_era import __version__, statistics
from braga_era.bridge.analytics import Analytics
from braga_era.bridge import protocol2
from braga_era.bridge.worker2 import Worker2
from braga_era.multiseason import groups
from braga_era.multiseason.schema import DDL
from braga_era.world.schema import DDL as WORLD
from test_bridge import Career, REQUESTERS, Transport

HEAD = 'a' * 64


@pytest.fixture
def group_world(tmp_path):
    path = tmp_path / 'test-world.sqlite'
    with sqlite3.connect(path) as db:
        db.executescript(WORLD + DDL)
        clubs = [f'club:{i}' for i in range(1, 5)]
        db.executemany('INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)',
                       [(key, name, name, i, None, 60, 0, '{}')
                        for i, (key, name) in enumerate(zip(clubs, ['Vasco', 'B', 'C', 'D']), 1)])
        db.execute("INSERT INTO ms_seasons VALUES(2028,'active',NULL)")
        db.execute("INSERT INTO ms_editions VALUES('LIB:2028','LIB',2028,'groups_knockout','{}','active',NULL)")
        db.execute("INSERT INTO ms_editions VALUES('LEAGUE:2028','LEAGUE',2028,'league','{}','active',NULL)")
        db.executemany("INSERT INTO ms_entries VALUES('LEAGUE:2028',?,'test','{}')", [(c,) for c in clubs])
        pairs = [(home, away) for home in clubs for away in clubs if home != away]
        for i, (home, away) in enumerate(pairs):
            db.execute("""INSERT INTO ms_fixtures VALUES(?,'LIB:2028','GROUP:5',?,NULL,?,?,
                        '2028-04-01 16:00',?,?,?,NULL)""",
                       (f'ms:{i}', i + 1, home, away, 'final' if i < 6 else 'scheduled',
                        1 if i < 6 else None, 0 if i < 6 else None))
        for pid, name, club in [(11, 'Nuno', clubs[0]), (12, 'Nuno', clubs[1])]:
            db.execute('INSERT INTO world_players VALUES(?,?,?,0,?,?)',
                       (pid, club, pid, json.dumps({'name': name, 'ovr': 72}), '{}'))
        performance = dict(player_id=11, club_key=clubs[0], starter=True, seconds_played=2700,
                           goals=1, assists=0, shots=2, on_target=1, saves=0, yellows=0,
                           red=False, injured=False, rating=8, xg=.3)
        db.execute("INSERT INTO ms_executions VALUES('ms:0','{}','','{}','{}',?,'')",
                   (json.dumps({'performances': [performance], 'events': []}),))
    db.close()
    return path


def test_group_5_partial_uses_committed_ranking(group_world):
    from braga_era.db import connect_read_only
    with connect_read_only(group_world) as db:
        args = {'dataset': 'standings', 'competition': 'LIB', 'group': 5}
        rows, metadata = statistics.select(db, args, set(), 2028)
        assert [r['club'] for r in rows] == [r['club'] for r in groups.table(db, 'LIB:2028', 'GROUP:5', require_complete=False)]
        assert metadata['played_fixtures'] == 6 and metadata['scheduled_fixtures'] == 12 and not metadata['complete']
        assert sum(r['gf'] for r in rows) == sum(r['ga'] for r in rows) == 6
        assert sum(r['played'] for r in rows) == 12
        assert sum(r['wins'] for r in rows) == sum(r['losses'] for r in rows) == 6
        with pytest.raises(statistics.QueryError, match='narration'):
            statistics.select(db, args, {'ms:0'}, 2028)
        with pytest.raises(statistics.QueryError, match='committed draw'):
            statistics.select(db, {**args, 'group': 4}, set(), 2028)


def test_player_coverage_and_exact_minutes(group_world):
    from braga_era.db import connect_read_only
    with connect_read_only(group_world) as db:
        args = {'dataset': 'player_stats', 'club': 'Vasco', 'season': 2028}
        (p,), coverage = statistics.select(db, args, set(), 2028)
        assert (p['goals'], p['assists'], p['minutes'], p['xg_per_90']) == (1, 0, 45, .6)
        assert coverage['fixtures_with_performances'] == 1 < coverage['final_fixtures_in_scope']
        assert statistics.select(db, {**args, 'player': 12}, set(), 2028)[0] == []
        with pytest.raises(statistics.QueryError, match='Matching IDs: 11, 12'):
            statistics.select(db, {**args, 'player': 'Nuno'}, set(), 2028)
        (p,), _ = statistics.select(db, {'dataset': 'squad', 'club': 'Vasco'}, set(), 2028)
        assert p['ovr'] == 72 and p['state']['fitness'] is None and p['active_contract'] is None


def test_issue_107_result_shape_through_worker(group_world, tmp_path):
    from braga_era.season_gameplay import table
    class RegisteredTableCareer(Career):
        def play(self, view, fixture=None, page_id=None):
            assert view == 'table'
            with sqlite3.connect(':memory:') as registry:
                registry.execute('CREATE TABLE cursors(fixture,sequence)')
                return table(registry, {'database': group_world, 'season': 2028})

    career = RegisteredTableCareer()
    transport = Transport()
    worker = Worker2(transport, career, tmp_path / 'bridge.sqlite', REQUESTERS)
    legacy = protocol2.RESULT_KEYS - {'edition'}
    for seq, keys in [(1, legacy), (2, protocol2.RESULT_KEYS)]:
        worker.result_keys = keys
        issue = transport.add({'protocol': protocol2.PROTOCOL, 'career': career.career,
                               'expected_checkpoint': career.identity()['checkpoint'],
                               'request_id': str(uuid4()), 'sequence': seq, 'command': 'current_table', 'args': {}})
        worker.poll()
        reply = transport.result(issue)['response']
        if seq == 1:
            assert reply['status'] == 'refused'
            assert reply['result'] == {'error': 'COMMAND_REFUSED', 'resume_existing_delivery': True}
        else:
            assert reply['status'] == 'completed'
            assert reply['result']['edition'] == 'LEAGUE:2028'


def test_statistics_pages_and_boundaries(group_world, monkeypatch, tmp_path):
    from braga_era.db import connect_read_only, file_sha256

    hidden = set()
    @contextmanager
    def snapshot(career, checkpoint):
        with connect_read_only(group_world) as db:
            yield db, {'season': 2028, 'clock': '2028-04-01 18:00', 'database_sha256': file_sha256(group_world)}, hidden

    monkeypatch.setattr('braga_era.bridge.analytics.accepted_snapshot', snapshot)
    before = file_sha256(group_world)
    api = Analytics(Career())
    args = {'dataset': 'standings', 'competition': 'LIB', 'group': 5, 'limit': 2}
    first = api.query(args, HEAD)
    assert api.query(args, HEAD) == first
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: api.query(args, HEAD), range(2))) == [first, first]
    second = api.query({'cursor': first['next_cursor']}, HEAD)
    assert [r['rank'] for r in first['rows'] + second['rows']] == [1, 2, 3, 4]
    assert second['next_cursor'] is None
    assert api.query({'cursor': first['next_cursor']}, 'b' * 64)['error']['code'] == 'SNAPSHOT_MOVED'
    assert api.query({'cursor': 'tampered'}, HEAD)['error']['code'] == 'INVALID_CURSOR'
    assert api.query({**args, 'group': True}, HEAD)['error']['code'] == 'INVALID_FILTER'
    career = Career()
    transport = Transport()
    worker = Worker2(transport, career, tmp_path / 'ledger.sqlite', REQUESTERS)
    with sqlite3.connect(worker.path) as ledger:
        status = worker.status_document(ledger)
    assert status['worker_version'] == __version__
    assert status['career_statistics_available'] is True
    request = {'protocol': protocol2.PROTOCOL, 'career': career.career,
               'expected_checkpoint': career.identity()['checkpoint'], 'request_id': str(uuid4()),
               'sequence': 1, 'command': 'career_statistics', 'args': args}
    issue = transport.add(request)
    worker.poll()
    reply = transport.result(issue)
    assert worker.verify_response(reply)
    assert reply['response']['result']['career_statistics']['rows'] == first['rows']
    duplicate = transport.add(request)
    worker.poll()
    assert transport.result(duplicate) == reply
    assert career.position == 0
    hidden.add('ms:0')
    assert api.query({'cursor': first['next_cursor']}, HEAD)['error']['code'] == 'SNAPSHOT_MOVED'
    assert file_sha256(group_world) == before


def test_team_and_recorded_changes(group_world):
    from braga_era.db import connect_read_only
    with sqlite3.connect(group_world) as writer:
        writer.execute("INSERT INTO ms_transfers VALUES('movement',11,'club:2','club:1','2028-01-18','transfer','{}')")
        writer.execute("""INSERT INTO ms_attributes VALUES(11,2028,'{"ovr":70}','{"ovr":72,"club_key":"club:1"}','{}')""")
    writer.close()
    with connect_read_only(group_world) as db:
        rows, _ = statistics.select(db, {'dataset': 'team_record', 'club': 'Vasco'}, set(), 2028)
        assert [(r['venue'], r['played'], r['wins'], r['clean_sheets']) for r in rows] == [
            ('home', 3, 3, 3), ('away', 1, 0, 0)]
        (trade,), _ = statistics.select(db, {'dataset': 'transfers', 'club': 'Vasco'}, set(), 2028)
        assert trade['id'] == 'movement' and trade['seller_name'] == 'B'
        (change,), _ = statistics.select(db, {'dataset': 'development', 'club': 'Vasco',
                                             'sort': 'ovr_delta', 'player': 11}, set(), 2028)
        assert change['ovr_delta'] == 2 and change['changes'] == {'ovr': {'before': 70, 'after': 72}}


def test_transport_page_bound(monkeypatch):
    @contextmanager
    def snapshot(career, checkpoint):
        yield None, {'season': 2028, 'clock': '2028-04-01 18:00', 'database_sha256': HEAD}, set()

    rows = [{'index': i, 'sample': 'x' * 1400} for i in range(75)]
    monkeypatch.setattr('braga_era.bridge.analytics.accepted_snapshot', snapshot)
    monkeypatch.setattr(statistics, 'select', lambda *args: (rows, {}))
    api = Analytics(Career())
    page = api.query({'dataset': 'editions', 'limit': 30}, HEAD)
    returned = []
    while True:
        assert len(json.dumps(page).encode()) < 33000
        returned.extend(page['rows'])
        if not page['next_cursor']:
            break
        page = api.query({'cursor': page['next_cursor']}, HEAD)
    assert returned == rows


def test_storage_failure_is_safe_and_actionable(monkeypatch):
    def unavailable(career, checkpoint):
        raise OSError('private diagnostic path')

    monkeypatch.setattr('braga_era.bridge.analytics.accepted_snapshot', unavailable)
    result = Analytics(Career()).query({'dataset': 'editions'}, HEAD)
    assert result['error']['code'] == 'SNAPSHOT_UNAVAILABLE'
    assert 'private diagnostic path' not in json.dumps(result)
