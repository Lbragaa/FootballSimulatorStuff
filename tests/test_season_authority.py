"""Real lineage parent, exact season approval, isolated bridge and DEV restore."""
from contextlib import closing
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import uuid4

import pytest

from braga_era import lineage, season_authority as seasons
from braga_era.bridge.career import Career
from braga_era.bridge.protocol2 import parse, role, schema
from braga_era.bridge.worker2 import Worker2
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.multiseason import store
from braga_era.world.storage import process_lock
from test_bridge import Transport, REQUESTERS

KEY = b'TEST SEASON BOUNDARY SIGNER ONLY!!' * 2


def test_policy_commits_migration_schema_and_disables_production():
    policy = seasons.policy()
    assert policy['migration_schema_sha256'] == digest(store.DDL)
    assert policy['test_only'] and not policy['production_acceptance_enabled']


@pytest.fixture(scope='module')
def completed(accepted_path, tmp_path_factory):
    root = tmp_path_factory.mktemp('season-authority')
    reg = root/'authority/registry.sqlite'
    try:
        lineage.provision(reg, KEY, test_only=True, commissioner='SIMULATED',
                          career_id='season-boundary-test', seed='season-boundary-fixed-v1')
        manifest = lineage.prepare(reg, KEY, accepted_path, until='2027-12-31 23:59', execution_id='finish-2027')
        with lineage.access(reg, KEY) as (c, trusted):
            decision = lineage.expected_authorization(manifest, trusted)
        lineage.authorize(reg, KEY, accepted_path, manifest, decision, lineage.sign(KEY, decision))
        target = root/'completed-2027'
        lineage.execute(reg, KEY, 'finish-2027', target)
        decision = lineage.acceptance_template(reg, KEY, target)
        lineage.accept(reg, KEY, target, decision, lineage.sign(KEY, decision))
        # Fixture starts AFTER existing narration has been delivered. Seal the
        # exact final cursors, never modify the checkpoint/results or create scores.
        with connect_read_only(target/'payload/database.sqlite') as db:
            cursors = [tuple(r) for r in db.execute('SELECT fixture_key,result_sha256 FROM world_receipts')]
            maxima = dict(db.execute('SELECT fixture_key,max(sequence) FROM world_events GROUP BY fixture_key'))
        with lineage.access(reg, KEY, True) as (c, trusted):
            c.executemany('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',
                          [(r[0], r[1], maxima[r[0]]) for r in cursors])
            lineage.seal_cursors(c, trusted, KEY)
        yield SimpleNamespace(root=root, registry=reg, parent=target,
                              parent_hash=file_sha256(target/'payload/database.sqlite'))
    finally:
        # This module owns precisely this temporary subtree; no retained DBs.
        if root.resolve().parent != tmp_path_factory.getbasetemp().resolve() or not root.name.startswith('season-authority'):
            raise ValueError('Unsafe season authority test cleanup target')
        shutil.rmtree(root)


@pytest.fixture
def career(completed, tmp_path):
    reg = tmp_path/'authority/registry.sqlite'
    reg.parent.mkdir()
    shutil.copyfile(completed.registry, reg)
    return Career(reg, KEY, 'season-boundary-test', True)


def approval(career, completed, request_id=None):
    manifest = seasons.prepare(career.registry, KEY, completed.parent, request_id or str(uuid4()))
    return manifest, lineage.signed(seasons.authorization(manifest), KEY)


def test_exact_approval_retry_crash_claims_and_seed(career, completed):
    before = career.identity()
    manifest, proof = approval(career, completed)
    assert manifest['immediate_parent_sha256'] == before['checkpoint']
    with lineage.access(career.registry, KEY) as (c, trusted):
        assert manifest['career_seed_sha256'] == digest(trusted['seed'])
    with pytest.raises(RuntimeError, match='before commit'):
        seasons.authorize(career.registry, KEY, completed.parent, manifest, proof, crash='before_commit')
    with lineage.access(career.registry, KEY) as (c, trusted):
        assert not c.execute("SELECT 1 FROM batches WHERE state='season_authorized'").fetchone()
    with pytest.raises(RuntimeError, match='after commit'):
        seasons.authorize(career.registry, KEY, completed.parent, manifest, proof, crash='after_commit')
    receipt = seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)
    assert receipt == seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)
    assert career.identity() == before
    assert seasons.inspect(career)['test_policy_authorized']
    other, other_proof = approval(career, completed)
    with pytest.raises(ValueError, match='already claimed'):
        seasons.authorize(career.registry, KEY, completed.parent, other, other_proof)
    with pytest.raises(ValueError, match='not execution-authorized'):
        lineage.execute(career.registry, KEY, 'season:'+manifest['request_id'], completed.root/'must-not-execute')
    with lineage.access(career.registry, KEY) as (c, trusted):
        assert c.execute("SELECT count(*) FROM decisions WHERE kind='season_policy'").fetchone()[0] == 1
    assert file_sha256(completed.parent/'payload/database.sqlite') == completed.parent_hash


def test_signed_policy_rejection_and_unknown_seed(career, completed, accepted_path):
    manifest, proof = approval(career, completed)
    with pytest.raises(ValueError, match='signature'):
        seasons.authorize(career.registry, KEY, completed.parent, manifest,
                          {'document': proof['document'], 'signature': '0'*64})
    changed = {**manifest, 'career_seed_sha256': '0'*64}
    with pytest.raises(ValueError, match='Exact signed'):
        seasons.authorize(career.registry, KEY, completed.parent, changed,
                          lineage.signed(seasons.authorization(changed), KEY))
    with lineage.access(career.registry, KEY) as (c, trusted):
        assert not c.execute("SELECT 1 FROM batches WHERE state='season_authorized'").fetchone()
    with pytest.raises(ValueError, match='Stale original root'):
        seasons.prepare(career.registry, KEY, accepted_path, str(uuid4()))


def test_unrevealed_results_and_pending_season_fail_closed(career, completed, accepted_path, tmp_path):
    with lineage.access(career.registry, KEY, True) as (c, trusted):
        c.execute('UPDATE cursors SET sequence=0 WHERE fixture=(SELECT fixture FROM cursors LIMIT 1)')
        lineage.seal_cursors(c, trusted, KEY)
    status = seasons.inspect(career)
    assert 'unrevealed_match_narration' in status['blockers']
    assert 'season_review' not in status
    assert not status['automatic_transition_allowed']
    with pytest.raises(ValueError, match='unrevealed'):
        approval(career, completed)
    reg = tmp_path/'incomplete/registry.sqlite'
    lineage.provision(reg, KEY, test_only=True, commissioner='SIMULATED', career_id='incomplete', seed='fixed')
    with pytest.raises(ValueError, match='closure blocked'):
        seasons.prepare(reg, KEY, accepted_path, str(uuid4()))


def test_authority_fencing_and_production_refusal(career, completed):
    manifest, proof = approval(career, completed)
    with lineage.access(career.registry, KEY, True) as (c, trusted):
        c.execute('UPDATE authority SET active=0')
        lineage.seal_authority(c, KEY)
    with pytest.raises(ValueError, match='fenced'):
        seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)
    with closing(lineage.connect(career.registry)) as c:
        c.execute('UPDATE authority SET active=1,test_only=0')
        lineage.seal_authority(c, KEY)
    with pytest.raises(ValueError, match='TEST-only'):
        seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)


def test_concurrent_runner_cannot_claim_parent(career, completed):
    manifest, proof = approval(career, completed)
    with process_lock(career.registry.parent):
        with pytest.raises(RuntimeError, match='Another world runner'):
            seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)
    seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)


def test_authorized_migration_independent_restore_no_acceptance(career, completed, tmp_path, monkeypatch):
    manifest, proof = approval(career, completed)
    destination = tmp_path/'candidate'
    with pytest.raises(ValueError, match='authorization required'):
        seasons.rehearse(career.registry, KEY, manifest['request_id'], destination)
    seasons.authorize(career.registry, KEY, completed.parent, manifest, proof)
    original_run = store.run
    def interrupted(*args, **kwargs):
        original_run(*args, **kwargs)
        raise RuntimeError('Interrupted after committed season migration')
    monkeypatch.setattr(store, 'run', interrupted)
    with pytest.raises(RuntimeError, match='after committed'):
        seasons.rehearse(career.registry, KEY, manifest['request_id'], destination)
    monkeypatch.setattr(store, 'run', original_run)
    response = seasons.rehearse(career.registry, KEY, manifest['request_id'], destination)
    assert response == seasons.rehearse(career.registry, KEY, manifest['request_id'], destination)
    with connect_read_only(destination/'database.sqlite') as c:
        assert c.execute('SELECT season,state FROM ms_seasons ORDER BY season').fetchall()[1][:] == (2028, 'preparing')
        assert c.execute('SELECT seed FROM ms_meta').fetchone()[0] == c.execute('SELECT seed FROM world_info').fetchone()[0]
    store.export(destination, tmp_path/'portable', KEY)
    restored = store.restore(tmp_path/'portable', tmp_path/'restored', KEY)
    assert restored['independent_replay'] and not restored['acceptance_eligible']
    assert restored['world_sha256'] == response['document']['candidate']['world_sha256']
    assert career.identity()['checkpoint'] == manifest['immediate_parent_sha256']
    assert file_sha256(completed.parent/'payload/database.sqlite') == completed.parent_hash
    with pytest.raises(ValueError, match='original season candidate'):
        seasons.rehearse(career.registry, KEY, manifest['request_id'], tmp_path/'other')


def test_bridge_signed_read_retry_with_no_controls(career, tmp_path):
    transport = Transport()
    worker = Worker2(transport, career, tmp_path/'bridge.sqlite', REQUESTERS)
    request = {'protocol': 'braga-bridge-2', 'career': career.career,
               'request_id': str(uuid4()), 'sequence': 1, 'expected_checkpoint': career.identity()['checkpoint'],
               'command': 'season_status', 'args': {}}
    assert parse(json.dumps(request)) == request
    assert role('season_status') == 'read'
    assert any(b['properties']['command']['const'] == 'season_status' for b in schema()['oneOf'])
    original = file_sha256(career.registry)
    issue = transport.add(request)
    worker.poll()
    result = transport.result(issue)
    assert worker.verify_response(result)
    assert result['response']['status'] == 'completed'
    assert result['response']['result']['season_status']['phase'] == 'transition_approval_required'
    assert not result['response']['result']['season_status']['automatic_transition_allowed']
    review = result['response']['result']['season_status']['season_review']
    assert review['complete'] and len(review['standings']) == 20
    assert all(r['played'] == 38 for r in review['standings'])
    assert file_sha256(career.registry) == original
    duplicate = transport.add(request)
    worker.poll()
    assert transport.result(duplicate) == result
    assert file_sha256(career.registry) == original


def test_corrupted_parent_refused(career, completed, tmp_path):
    # Copy only a small supporting document to a fake parent, not a whole save.
    fake = tmp_path/'corrupt/payload'
    fake.mkdir(parents=True)
    shutil.copyfile(completed.parent/'payload/checkpoint.json', fake/'checkpoint.json')
    data = json.loads((fake/'checkpoint.json').read_text())
    data['clock'] = '2028-01-01 00:00'
    (fake/'checkpoint.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='unaccepted'):
        seasons.prepare(career.registry, KEY, fake.parent, str(uuid4()))
