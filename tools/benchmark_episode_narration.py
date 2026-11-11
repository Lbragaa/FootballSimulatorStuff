"""Compare the deployed and candidate registered narration loops on disposable data."""

from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from statistics import median
import subprocess
import tempfile
from time import perf_counter, process_time
from types import ModuleType
from unittest.mock import patch

from braga_era import lineage, season_gameplay, season_lineage
from braga_era.db import file_sha256
from braga_era.history import canonical_json, digest
from braga_era.multiseason.schema import DDL
from braga_era.world.schema import DDL as WORLD

KEY = b'public-benchmark-only-signer-for-episode-tests'
CHECKPOINT = lineage.ROOT


def build(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(WORLD + DDL)
        db.execute("INSERT INTO ms_editions VALUES('LEAGUE:2028','LEAGUE',2028,'league','{}','active',NULL)")
        # The unused payload models reading a larger immutable database from
        # disk. It is neither parsed as a result nor included in public output.
        db.execute('CREATE TABLE padding(blob)')
        db.execute('INSERT INTO padding VALUES(zeroblob(16777216))')
        for i in range(20):
            club = f'club:{30+i}'
            db.execute('INSERT INTO ms_entries VALUES(?,?,?,?)', ('LEAGUE:2028', club, 'test', '{}'))
            db.execute('INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)', (club, club, club, None, None, 1, 1, '{}'))
        for i in range(18):
            fixture = f'ms:{i:02}'
            db.execute("INSERT INTO ms_fixtures VALUES(?,'LEAGUE:2028','R10',10,NULL,?,?,'2028-05-14 16:00','final',1,0,NULL)",
                       (fixture, f'club:{30+i}', f'club:{31+i}'))
            events = [{'sequence': n, 'kind': 'PLAY', 'on_field_home': list(range(11)),
                       'on_field_away': list(range(11, 22))} for n in range(1, 65)]
            events[-1]['kind'] = 'FINAL_WHISTLE'
            bundle = {'events': events, 'score': [1, 0], 'resolution': {}}
            db.execute('INSERT INTO ms_executions VALUES(?,?,?,?,?,?,?)',
                       (fixture, '{}', '', '{}', '{}', canonical_json(bundle), digest(bundle)))


def measure(module, database, registry, fast):
    lineage.provision(registry, KEY, test_only=True, commissioner='Benchmark', career_id='episode-test', seed='test')
    original = file_sha256(database)
    info = {'database': database, 'checkpoint': CHECKPOINT, 'season': 2028,
            'metadata': {'database_sha256': original}}
    calls = defaultdict(int)
    seconds = defaultdict(float)

    def parent(*args):
        started = perf_counter()
        calls['parent_reads'] += 1
        if file_sha256(database) != original:
            raise ValueError('Benchmark world changed')
        seconds['parent_hash_subset'] += perf_counter() - started
        return info

    def view():
        if fast:
            return module.episode_view(registry, KEY)
        with lineage.access(registry, KEY) as (c, t):
            state = module.state(c, parent(c, t, KEY, None))
        with lineage.access(registry, KEY, True) as (c, t):
            lineage.check_cursors(c, t, KEY)
            events = module.gameplay(c, t, KEY, None, 'next', None, 1, None)['events']
        return state, events

    wall, cpu = perf_counter(), process_time()
    with patch.object(season_lineage, 'parent_info', parent), patch.object(season_lineage, 'current', lambda *a: (parent(*a), None)):
        while True:
            started = perf_counter()
            _, events = view()
            seconds['state_and_agenda'] += perf_counter() - started
            if not events or events[0]['kind'] != 'narration':
                break
            fixture = events[0]['key']
            calls['receipts'] += 1
            page_id = str(calls['receipts'])
            started = perf_counter()
            if fast:
                module.finish_background(registry, KEY, CHECKPOINT, fixture, page_id)
            else:
                with lineage.access(registry, KEY, True) as (c, t):
                    lineage.check_cursors(c, t, KEY)
                    module.gameplay(c, t, KEY, None, 'narrate', fixture, 20, page_id)
            seconds['narration'] += perf_counter() - started
    seconds['wall'] = perf_counter() - wall
    seconds['cpu'] = process_time() - cpu
    with lineage.access(registry, KEY) as (c, t):
        lineage.check_cursors(c, t, KEY)
        assert t['head'] == CHECKPOINT and file_sha256(database) == original
        cursors = [tuple(r) for r in c.execute('SELECT * FROM cursors ORDER BY fixture')]
    return dict(seconds), dict(calls), cursors


def main():
    source = subprocess.check_output(['git', 'show', 'ca26e0c:braga_era/season_gameplay.py'])
    old = ModuleType('braga_era._deployed_season_gameplay')
    exec(compile(source, '<deployed 0.13.6 season gameplay>', 'exec'), old.__dict__)
    with tempfile.TemporaryDirectory(prefix='braga-episode-bench-') as tmp:
        root = Path(tmp)
        database = root / 'world.sqlite'
        build(database)
        samples = {'before': [], 'after': []}
        for i in range(5):
            results = {}
            for name, module in ([('before', old), ('after', season_gameplay)] if i % 2 == 0 else
                                 [('after', season_gameplay), ('before', old)]):
                module._event_counts.cache_clear()
                results[name] = measure(module, database, root / f'{name}-{i}.sqlite', name == 'after')
                samples[name].append(results[name][0])
            assert results['before'][2] == results['after'][2] and len(results['after'][2]) == 18
        print(json.dumps({name: {
            'counts': results[name][1],
            'median_seconds': {k: round(median(r[k] for r in rows), 3) for k in rows[0]},
            'max_seconds': {k: round(max(r[k] for r in rows), 3) for k in rows[0]},
        } for name, rows in samples.items()}, indent=2))


if __name__ == '__main__':
    main()
