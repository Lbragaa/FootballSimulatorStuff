from contextlib import closing
import sqlite3
from uuid import uuid4

import pytest

from braga_era import lineage, season_lineage
from braga_era.db import file_sha256
from braga_era.history import canonical_json, digest
from braga_era.multiseason import fork, operations, store, timeline
from braga_era.multiseason.execution import timeline_entropy
from braga_era.multiseason.registered import DDL, PROFILE, policy
from braga_era.world.schema import DDL as WORLD

SOURCE_KEY = b'test-source-authority-keep-separate'
TEST_KEY = b'test-branch-authority-keep-separate'
CHECKPOINT = 'a' * 64
ENTROPY = 'b' * 64


@pytest.fixture
def accepted(tmp_path, monkeypatch):
    path = tmp_path/'parent.sqlite'
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(WORLD + DDL)
        db.execute("INSERT INTO ms_meta VALUES(1,?,?,?,?,?,?,0)",
                   (PROFILE, CHECKPOINT, ENTROPY, canonical_json(policy(False)), 'original', '2028-04-09 17:33:00'))
        db.execute("INSERT INTO ms_operations VALUES(1,'original','history','{}','{}','first','last','sig')")
    sha = file_sha256(path)
    monkeypatch.setattr(timeline, 'accepted_package', lambda *_: (
        {'state': {'database.sqlite': {'sha256': sha}}, 'metadata': {'clock': '2028-04-09 17:33:00'}},
        tmp_path, 'original', 'test-career'))
    import shutil
    monkeypatch.setattr(timeline.season_objects, 'materialize', lambda pool, desc, dest: shutil.copyfile(path, dest))
    # Exercise the same signed transaction/replay path with a tiny operation.
    monkeypatch.setattr(operations, 'apply', lambda db, kind, args: {
        'derived': digest([db.execute('SELECT seed FROM ms_meta').fetchone()[0], timeline_entropy.get(), args])})
    return path, sha


def test_same_and_alternate_seed_branches_preserve_source(accepted, tmp_path):
    original, sha = accepted
    results = []
    for name, mode, seed in [('same', 'same', None), ('first', 'alternate', 'c'*64),
                             ('repeat', 'alternate', 'c'*64), ('different', 'alternate', 'd'*64)]:
        target = tmp_path/name
        source_registry = tmp_path/'source'/'authority'/'registry.sqlite'
        decision = timeline.rehearse(source_registry, SOURCE_KEY, CHECKPOINT, target, TEST_KEY,
                                     seed_mode=mode, branch_seed=seed)
        assert decision['source_entropy_parent'] == ENTROPY
        world = target/'world'
        request = str(uuid4())
        with pytest.raises(RuntimeError, match='after commit'):
            store.run(world, TEST_KEY, request, 'demo', {'fixture': 'TEST'}, crash='after_commit')
        results.append(store.run(world, TEST_KEY, request, 'demo', {'fixture': 'TEST'}))
        proof = store.validate(world, TEST_KEY)
        assert proof['test_only'] and proof['independent_replay'] and not proof['acceptance_eligible']
        with pytest.raises(FileExistsError):
            timeline.rehearse(source_registry, SOURCE_KEY, CHECKPOINT, target, TEST_KEY, seed_mode=mode)
    assert results[1] == results[2]
    assert len({r['derived'] for r in (results[0], results[1], results[3])}) == 3
    assert file_sha256(original) == sha
    assert timeline_entropy.get() is None


def test_new_marker_cannot_be_promoted(accepted, tmp_path):
    target = tmp_path/'scratch'
    timeline.rehearse(tmp_path/'source'/'authority'/'registry.sqlite', SOURCE_KEY,
                      CHECKPOINT, target, TEST_KEY, seed_mode='same')
    world, marker = store.authenticated(target/'world', TEST_KEY)
    assert marker['decision']['action'] == fork.REHEARSAL
    with pytest.raises(ValueError, match='Untrusted timeline base'):
        fork.authenticate(world, {**marker, 'acceptance_eligible': True}, TEST_KEY)
    with pytest.raises(ValueError, match='Exact episode #81'):
        season_lineage.stage_episode81_import(None, TEST_KEY, world, tmp_path/'official', str(uuid4()))


def test_named_savepoint_is_signed_and_immutable(accepted, tmp_path):
    registry = tmp_path/'source'/'authority'/'registry.sqlite'
    value = timeline.bookmark(registry, SOURCE_KEY, CHECKPOINT, tmp_path, 'before-lib',
                              description='Before the group stage')
    path = tmp_path/'before-lib.json'
    assert lineage.check_signed(lineage.read_json(path), SOURCE_KEY) == value
    with pytest.raises(ValueError):
        timeline.bookmark(registry, SOURCE_KEY, 'e'*64, tmp_path, 'before-lib')
    with pytest.raises(ValueError, match='short save name'):
        timeline.bookmark(registry, SOURCE_KEY, CHECKPOINT, tmp_path, '../escape')


def test_archive_requires_exact_replay_report(accepted, tmp_path):
    target = tmp_path/'test-branch'
    timeline.rehearse(tmp_path/'source'/'authority'/'registry.sqlite', SOURCE_KEY,
                      CHECKPOINT, target, TEST_KEY, seed_mode='same')
    world = target/'world'
    proof = store.validate(world, TEST_KEY)
    report = {'verified': True, 'operation_count': proof['operations'], 'world_sha256': proof['world_sha256']}
    archive = tmp_path/'test.zip'
    with pytest.raises(ValueError, match='exact world tables'):
        timeline.archive_rehearsal(world, TEST_KEY, lineage.signed({**report, 'world_sha256': 'bad'}, TEST_KEY), archive)
    assert timeline.archive_rehearsal(world, TEST_KEY, lineage.signed(report, TEST_KEY), archive) == file_sha256(archive)
