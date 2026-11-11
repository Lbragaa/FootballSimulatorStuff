from contextlib import closing
import json
import sqlite3

import pytest

from braga_era import lineage, season_gameplay, season_lineage
from braga_era.db import file_sha256
from braga_era.history import canonical_json, digest
from braga_era.multiseason.schema import DDL
from braga_era.world.schema import DDL as WORLD

KEY = b'public-test-episode-background-signing-key'


@pytest.fixture
def background(tmp_path, monkeypatch):
    database = tmp_path / 'world.sqlite'
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript(WORLD + DDL)
        db.execute("INSERT INTO ms_editions VALUES('LEAGUE:2028','LEAGUE',2028,'league','{}','active',NULL)")
        for fixture, home, kickoff in [('ms:vasco', 'club:15', '2028-04-01 16:00'),
                                       ('ms:other', 'club:2', '2028-04-01 16:00'),
                                       ('ms:later', 'club:4', '2028-04-02 16:00')]:
            db.execute("""INSERT INTO ms_fixtures VALUES(?,'LEAGUE:2028','R1',1,NULL,?,'club:3',?,'final',1,0,NULL)""",
                       (fixture, home, kickoff))
            bundle = {'events': [{'kind': 'KICKOFF'}, *[{'kind': 'PLAY'}] * 62, {'kind': 'FINAL_WHISTLE'}],
                      'score': [1, 0], 'resolution': {}}
            db.execute('INSERT INTO ms_executions VALUES(?,?,?,?,?,?,?)',
                       (fixture, '{}', '', '{}', '{}', canonical_json(bundle), digest(bundle)))
    registry = tmp_path / 'registry.sqlite'
    lineage.provision(registry, KEY, test_only=True, commissioner='Test', career_id='episode-test', seed='test-only')
    info = {'database': database, 'checkpoint': lineage.ROOT, 'season': 2028,
            'metadata': {'database_sha256': file_sha256(database)}}
    monkeypatch.setattr(season_lineage, 'current', lambda *args: (info, None))
    monkeypatch.setattr(season_lineage, 'parent_info', lambda *args: info)
    return registry, database


def test_background_is_bound_to_head_and_earliest_group(background):
    registry, database = background
    before = file_sha256(database)

    def finish(fixture, page_id):
        return season_gameplay.finish_background(registry, KEY, lineage.ROOT, fixture, page_id)

    for fixture in ('ms:vasco', 'ms:later'):
        with pytest.raises(ValueError, match='eligible non-Vasco'):
            finish(fixture, fixture)
    with pytest.raises(ValueError, match='parent changed'):
        season_gameplay.finish_background(registry, KEY, '0' * 64, 'ms:other', 'stale')
    page = finish('ms:other', 'episode-background')
    assert page['events'] == [] and page['postmatch_available']
    assert (page['consumed_from'], page['consumed_to']) == (0, 64)
    assert finish('ms:other', 'episode-background') == page
    with pytest.raises(ValueError, match='page binding changed'):
        finish('ms:later', 'episode-background')
    with lineage.access(registry, KEY) as (c, trusted):
        lineage.check_cursors(c, trusted, KEY)
        assert c.execute('SELECT revision FROM cursor_revision').fetchone()[0] == 1
        row = c.execute('SELECT * FROM narration_pages').fetchone()
        assert json.loads(row['response']) == page
        assert c.execute('SELECT fixture,sequence FROM cursors').fetchall()[0][:] == ('ms:other', 64)
        assert trusted['head'] == lineage.ROOT
    assert file_sha256(database) == before


def test_background_can_finish_an_already_started_result(background):
    registry, _ = background
    with lineage.access(registry, KEY, True) as (c, trusted):
        page = season_gameplay.gameplay(c, trusted, KEY, None, 'narrate', 'ms:other', 20, 'old-detail')
    assert len(page['events']) == 20 and not page['postmatch_available']
    final = season_gameplay.finish_background(registry, KEY, lineage.ROOT, 'ms:other', 'new-background')
    assert final['consumed_from'] == 20 and final['consumed_to'] == 64
