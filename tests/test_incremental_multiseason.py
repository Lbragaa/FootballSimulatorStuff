"""A signed parent attestation must never hide tampering or replace old replay."""
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import sqlite3
from uuid import uuid4
import pytest
from test_multiseason import parent,KEY,cmd,setup_edition
from braga_era.forward import sign
from braga_era.multiseason import store,incremental
from braga_era.db import connect_read_only


@pytest.fixture(autouse=True)
def release_large_case_files(tmp_path):
    yield
    # Only this test's own disposable directory; never the shared parent fixture.
    resolved=tmp_path.resolve()
    if not resolved.name.startswith('test_') or resolved.parent!=tmp_path.parent.resolve():raise ValueError('Unsafe test cleanup target')
    shutil.rmtree(resolved)


@pytest.fixture(scope='module')
def sealed_parent(parent,tmp_path_factory):
    root=tmp_path_factory.mktemp('sealed-parent-fixture');target=root/'world'
    policy=store.proposed_policy();decision=store.statement(parent,policy,'incremental-fixed-seed')
    store.create(parent,target,seed='incremental-fixed-seed',policy=policy,decision=decision,signature=sign(KEY,decision),test_key=KEY)
    edition=setup_edition(target)
    cmd(target,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    store.export(target,root/'portable',KEY)
    statement=incremental.seal_parent(root/'portable',root/'sealed',KEY)
    assert statement['full_parent_replay'] is True
    return root/'sealed'


def test_child_crash_exact_retry_full_replay_and_portable_restore(sealed_parent,tmp_path):
    target=tmp_path/'child';incremental.create(sealed_parent,target,KEY)
    incremental.run(target,KEY,str(uuid4()),'claim_group',{'kickoff':'2028-01-06 16:00'})
    request=str(uuid4());args={'kickoff':'2028-01-06 16:00'}
    with pytest.raises(RuntimeError,match='after commit'):incremental.run(target,KEY,request,'play_group',args,crash='after_commit')
    with ThreadPoolExecutor(2) as pool:
        replies=list(pool.map(lambda _:incremental.run(target,KEY,request,'play_group',args),range(2)))
    assert replies[0]==replies[1]
    with connect_read_only(target/'child/database.sqlite') as c:assert c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]==2
    verified=incremental.validate(target,KEY)
    assert verified['replayed_operations']==2 and verified['independent_suffix_replay']
    assert store.validate(target/'child',KEY)['world_sha256']==verified['world_sha256']
    exported=incremental.export(target,tmp_path/'package',KEY)
    restored=incremental.restore(tmp_path/'package',tmp_path/'restored',KEY)
    assert exported==restored==verified
    assert exported['acceptance_eligible'] is False
    (tmp_path/'package/unexpected.txt').write_text('TEST malformed inventory')
    with pytest.raises(ValueError,match='inventory'):incremental.restore(tmp_path/'package',tmp_path/'invalid-restore',KEY)
    assert not (tmp_path/'invalid-restore').exists()


@pytest.mark.parametrize('defect',['parent_bytes','seal_signature','child_history','operation_prefix','extra_private_file'])
def test_tampering_cannot_publish_or_reinterpret_parent(sealed_parent,tmp_path,defect):
    target=tmp_path/'child';incremental.create(sealed_parent,target,KEY)
    if defect=='parent_bytes':
        with sqlite3.connect(target/'parent/snapshot/database.sqlite') as c:c.execute("UPDATE ms_fixtures SET home_goals=99")
    elif defect=='seal_signature':
        path=target/'parent/seal.json';value=json.loads(path.read_text());value['signature']='0'*64;path.write_text(json.dumps(value))
    elif defect=='child_history':
        with sqlite3.connect(target/'child/database.sqlite') as c:c.execute("UPDATE ms_fixtures SET home_goals=99")
    elif defect=='operation_prefix':
        with sqlite3.connect(target/'child/database.sqlite') as c:c.execute("UPDATE ms_operations SET args_json='{}' WHERE sequence=1")
    else:(target/'child/TEST-secret.key').write_text('deliberate fake private file; must never export')
    with pytest.raises(ValueError):incremental.export(target,tmp_path/'must-not-publish',KEY)
    assert not (tmp_path/'must-not-publish').exists()
