"""Real lineage parent, exact season approval, isolated bridge and DEV restore."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import os
import stat
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


def test_standing_season_exact_preparation_crash_retry_and_revoke(career, completed, tmp_path):
    from braga_era import season_lineage as registered
    from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN
    from braga_era.bridge.automatic import Automatic
    from braga_era.bridge.control import Controls, PROFILE as CONTROL, OPERATIONS
    from braga_era.multiseason.lifecycle import RELEASE_PROPOSAL
    from test_bridge_worker2 import req, users

    clock = [1700000000]
    gate = HumanGate(tmp_path / 'human.sqlite', KEY, b'standing season TEST secret',
                     {'profile': HUMAN, 'career': career.career, 'test_only': True,
                      'repository_id': 1436541980, 'human_id': 78325376, 'human_login': 'Lbragaa'},
                     clock=lambda: clock[0])
    gate.initialize()
    with lineage.access(career.registry, KEY) as (_, trusted):
        policy = {'profile': CONTROL, 'action': 'approve_remote_control_policies', 'career': career.career,
                  'test_only': True, 'authority_key_sha256': trusted['key_hash'],
                  'policy_sha256': digest(json.loads(trusted['policy_json'])), 'repository_id': 1436541980,
                  'human_id': 78325376, 'human_login': 'Lbragaa', 'operations': OPERATIONS}
    receipt = tmp_path / 'control-policy.json'
    receipt.write_text(json.dumps(lineage.signed(policy, KEY)))
    controls = Controls(career, tmp_path / 'controls.sqlite', tmp_path / 'executions', receipt, gate, enabled=True)
    controls.initialize()
    automatic = Automatic(controls, tmp_path / 'automatic')
    automatic.initialize()
    transport = Transport()
    path = tmp_path / 'bridge.sqlite'

    def worker(crash=None):
        return Worker2(transport, career, path, users(), controls=controls, automatic=automatic, crash=crash)

    w = worker()
    sequence = 1

    def request(command, **args):
        nonlocal sequence
        r = req(career, command, sequence, **args)
        sequence += 1
        return r

    def deliver(r, status='completed'):
        issue = transport.add(r)
        w.poll()
        result = transport.result(issue)
        assert w.verify_response(result) and result['response']['status'] == status
        return result['response']['result']

    initial = career.identity()
    deliver(request('enable_automatic_gameplay', confirmation='ENABLE_AUTOMATIC_GAMEPLAY'))
    assert not deliver(request('automatic_seasons_status'))['automatic_seasons']
    deliver(request('advance_season'), 'refused')
    prep = deliver(request('prepare_season_transition', policy=RELEASE_PROPOSAL))
    exact = {k: prep[k] for k in ('preparation_id', 'manifest_sha256')}
    manual = deliver(request('request_authorize_season', **exact))['confirmation']
    opt_in = {'policy': RELEASE_PROPOSAL, 'confirmation': 'ENABLE_AUTOMATIC_SEASON_TRANSITIONS'}
    deliver(request('enable_automatic_seasons', **opt_in), 'refused')
    clock[0] = manual['expires_at_unix'] + 1
    enable = request('enable_automatic_seasons', **opt_in)
    assert deliver(enable)['automatic_seasons']
    with gate.access() as c:
        assert tuple(c.execute('SELECT state,proof FROM challenges WHERE id=?',
                               (manual['challenge_id'],)).fetchone()) == ('expired', None)
    assert career.identity() == initial
    deliver(request('advance_prepared_season', **{**exact, 'manifest_sha256': '0'*64}), 'refused')
    transition = request('advance_prepared_season', **exact)
    issue = transport.add(transition)
    pid = exact['preparation_id']
    destination = controls._destination(pid)
    for phase in ('authorize', 'candidate', 'accept'):
        with pytest.raises(RuntimeError, match='Injected bridge crash'):
            worker('after_standing_season_' + phase).poll()
        with lineage.access(career.registry, KEY) as (c, trusted):
            rows = c.execute('SELECT id,state,manifest FROM batches WHERE parent=?', (initial['checkpoint'],)).fetchall()
            assert len(rows) == 1 and rows[0]['id'] == 'season3:' + pid
            assert digest(json.loads(rows[0]['manifest'])) == exact['manifest_sha256']
            assert rows[0]['state'] == {'authorize': 'season_authorized_v3', 'candidate': 'season_candidate',
                                        'accept': 'accepted'}[phase]
            if phase != 'accept':
                assert trusted['head'] == initial['checkpoint']
    w = worker()
    w.poll()
    response = transport.result(issue)
    assert w.verify_response(response)
    result = response['response']['result']
    assert result['phase'] == 'season_transition_accepted' and result['season'] == 2028
    assert result['accepted_checkpoint'] == career.identity()['checkpoint'] != initial['checkpoint']
    assert result['preparation_id'] == pid and result['manifest_sha256'] == exact['manifest_sha256']
    assert result['candidate']['independent_delta_replay']
    duplicate = transport.add(transition)
    w.poll()
    assert transport.result(duplicate) == response
    assert not deliver(request('disable_automatic_seasons'))['automatic_seasons']
    assert deliver(enable)['automatic_seasons']  # original reply, without restoring the revoked grant
    assert not deliver(request('automatic_seasons_status'))['automatic_seasons']
    deliver(request('advance_season'), 'refused')
    archive = tmp_path / 'standing-season.zip'
    registered.export(career.registry, KEY, destination, archive)
    restored = registered.restore(career.registry, KEY, archive, tmp_path / 'standing-restored')
    assert restored['independent_restore'] and restored['checkpoint'] == result['accepted_checkpoint']
    backup = tmp_path / 'standing-backup'
    lineage.backup(career.registry, KEY, backup)
    with closing(lineage.connect(backup / 'authority.sqlite')) as c:
        audits = [(r['kind'], lineage.check_signed({'document': json.loads(r['document']),
                                                   'signature': r['signature']}, KEY))
                  for r in c.execute("SELECT * FROM decisions WHERE batch=? AND kind LIKE 'standing_season_%' ORDER BY id",
                                     ('season3:' + pid,))]
    assert [kind for kind, _ in audits] == ['standing_season_execution', 'standing_season_acceptance']
    assert all(doc['source_issue'] == issue and doc['grant']['scope']['policy'] == RELEASE_PROPOSAL
               and doc['request_id'] == transition['request_id'] for _, doc in audits)
    assert audits[1][1]['target_sha256'] == result['accepted_checkpoint']
    assert file_sha256(completed.parent / 'payload/database.sqlite') == completed.parent_hash


def test_registered_successor_episode_recovery_and_portability(career, completed, tmp_path):
    import time
    from braga_era import season_lineage as registered
    from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN
    from braga_era.bridge.control import Controls, PROFILE as CONTROL, OPERATIONS
    from braga_era.bridge.automatic import Automatic
    from braga_era.bridge.worker2 import Worker2
    from test_bridge_worker2 import req, users
    clubs=['club:1','club:2','club:3','club:15']
    operations=[{'kind':'continue_modeled_registrations','args':{'season':2028}},
        {'kind':'propose_pool','args':{'id':'registered-state-2028','season':2028,'competition':'STATE','clubs':clubs,'reason':'Explicit representative bridge scenario; not the full season'}},
        *[{'kind':'qualify','args':{'season':2028,'competition':'STATE','club':club,'source':{'type':'proposed_pool','pool':'registered-state-2028'}}} for club in clubs],
        {'kind':'edition','args':{'competition':'STATE','season':2028,'format':'league','clubs':clubs,'rules':{'legs':2,'final_legs':1,'neutral_final':False}}},
        {'kind':'schedule','args':{'edition':'STATE:2028','start':'2028-01-08 16:00','deadline':'2028-12-21 23:59'}}]
    request=str(uuid4());m=registered.prepare(career.registry,KEY,request,operations,transition=True,automatic_gameplay=True)
    before=career.identity()['checkpoint']
    registered.authorize(career.registry,KEY,m,lineage.signed(registered.authorization(m),KEY))
    target=tmp_path/'transition'
    with pytest.raises(RuntimeError,match='after operations'):
        registered.execute(career.registry,KEY,request,target,crash='after_operations')
    candidate=registered.execute(career.registry,KEY,request,target)
    decision=registered.acceptance_template(career.registry,KEY,target)
    with pytest.raises(ValueError,match='signature'):
        registered.accept(career.registry,KEY,target,decision,'0'*64)
    with pytest.raises(RuntimeError,match='after commit'):
        registered.accept(career.registry,KEY,target,decision,lineage.sign(KEY,decision),crash='after_commit')
    assert lineage.recover_acceptance(career.registry,KEY,target)['acceptance_restored']
    assert career.identity()['checkpoint']==candidate['checkpoint_sha256']!=before
    assert not (target/'world').exists()
    gate=HumanGate(tmp_path/'human.sqlite',KEY,b'public TEST ONLY secret',
        {'profile':HUMAN,'career':career.career,'test_only':True,'repository_id':1436541980,
         'human_id':78325376,'human_login':'Lbragaa'},clock=lambda:1700000000)
    gate.initialize()
    with lineage.access(career.registry,KEY) as (c,t):
        p={'profile':CONTROL,'action':'approve_remote_control_policies','career':career.career,'test_only':True,
           'authority_key_sha256':t['key_hash'],'policy_sha256':digest(json.loads(t['policy_json'])),
           'repository_id':1436541980,'human_id':78325376,'human_login':'Lbragaa','operations':OPERATIONS}
    receipt=tmp_path/'control-policy.json';receipt.write_text(json.dumps(lineage.signed(p,KEY)))
    controls=Controls(career,tmp_path/'controls.sqlite',tmp_path/'executions',receipt,gate,enabled=True);controls.initialize()
    auto=Automatic(controls,tmp_path/'automatic');auto.initialize()
    auto.set_mode(True,req(career,'enable_automatic_gameplay',1,confirmation='ENABLE_AUTOMATIC_GAMEPLAY'),1)
    transport=Transport();worker=Worker2(transport,career,tmp_path/'bridge.sqlite',users(),controls=controls,automatic=auto)
    r=req(career,'play_next_episode',1);issue=transport.add(r);worker.poll()
    response=transport.result(issue);assert worker.verify_response(response)
    assert response['response']['status']=='completed'
    episode=response['response']['result'];assert episode['episode_type']=='vasco_match'
    sections=episode['presentation'];events=[e for s in sections for e in s.get('events',[])]
    assert events[-1]['kind']=='FINAL_WHISTLE'
    assert next(i for i,s in enumerate(sections) if s['section']=='fulltime')>max(i for i,s in enumerate(sections) if s['section']=='vasco_timeline')
    assert all('score' not in e.get('details',{}) for e in events)
    replay=transport.add(r);worker.poll();assert transport.result(replay)==response
    with lineage.access(career.registry,KEY) as (c,t):path=Path(c.execute('SELECT path FROM accepted WHERE checkpoint=?',(t['head'],)).fetchone()[0])
    archive=tmp_path/'career.zip';exported=registered.export(career.registry,KEY,path,archive)
    restored=registered.restore(career.registry,KEY,archive,tmp_path/'restored')
    assert restored['independent_restore'] and restored['checkpoint']==career.identity()['checkpoint']
    assert exported['archive_bytes']<sum(p.stat().st_size for p in (tmp_path/'authority/season-cache').rglob('*.sqlite'))
    from braga_era.bridge.historical import HistoricalResults
    original_registry=file_sha256(career.registry)
    history=HistoricalResults(career).query({'season':2028,'club':'Vasco','limit':10})
    assert history['matches'] and all(r['season']==2028 for r in history['matches'])
    assert file_sha256(career.registry)==original_registry
    backup=tmp_path/'authority-backup';lineage.backup(career.registry,KEY,backup)
    with pytest.raises(ValueError,match='lost-authority'):
        lineage.restore_backup(backup,KEY,tmp_path/'refused-backup',expected_test_only=True)
    recovered=lineage.restore_backup(backup,KEY,tmp_path/'recovered-authority',expected_test_only=True,recover_lost_authority=True)
    assert lineage.inspect(recovered['registry'],KEY)['accepted_checkpoint']==career.identity()['checkpoint']
    assert file_sha256(completed.parent/'payload/database.sqlite')==completed.parent_hash


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
        def readonly_retry(function,path,error):
            target=Path(path).resolve()
            if target!=root.resolve() and root.resolve() not in target.parents:raise ValueError('Unsafe readonly cleanup target')
            if not isinstance(error[1],PermissionError):raise error[1]
            os.chmod(target,stat.S_IRWXU)
            function(path)
        # OneDrive can mark even empty published fixture directories readonly.
        # Clear only this verified owned subtree before removing its copies.
        for owned in [root,*root.rglob('*')]:
            resolved=owned.resolve()
            if resolved!=root.resolve() and root.resolve() not in resolved.parents:raise ValueError('Redirected cleanup path')
            os.chmod(owned,stat.S_IRWXU)
        shutil.rmtree(root,onerror=readonly_retry)


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
