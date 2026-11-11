"""Register the exact verified Libertadores archive under a separate signer."""
import argparse
import json
from pathlib import Path
import secrets
import shutil
import tempfile
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from braga_era import lineage, season_lineage as seasons, season_objects, season_gameplay
from braga_era.bridge.__main__ import config
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.multiseason import fork, groups, store, timeline
from braga_era.multiseason.registered import policy
from braga_era.seasons import fingerprints
from .register_episode81_fork import bridge


def verify_source(archive, test_key, old, target):
    if file_sha256(archive) != fork.QUALIFIED_ARCHIVE:
        raise ValueError('Wrong qualifying archive')
    names = {'database.sqlite', 'parent.sqlite', 'development.json'}
    target.mkdir()
    with ZipFile(archive) as zipped:
        if set(zipped.namelist()) != names | {'archive.json'}:
            raise ValueError('Unexpected qualifying archive inventory')
        manifest = lineage.check_signed(json.loads(zipped.read('archive.json')), test_key)
        report = lineage.check_signed(manifest['verification'], test_key)
        if (set(manifest['files']) != names or manifest['source_checkpoint'] != fork.QUALIFIED_SOURCE
                or manifest['seed_sha256'] != fork.QUALIFIED_SEED
                or not report['verified'] or not report['test_only'] or report['rank'] != 1):
            raise ValueError('Qualifying archive verification differs')
        for name, expected in manifest['files'].items():
            with zipped.open(name) as source, (target/name).open('xb') as out:
                shutil.copyfileobj(source,out)
            if file_sha256(target/name) != expected:
                raise ValueError('Qualifying archive member differs')
    _, marker = store.authenticated(target,test_key)
    old_key = Path(old['key_file']).read_bytes()
    package, _, _, _ = timeline.accepted_package(old['registry'],old_key,fork.QUALIFIED_SOURCE)
    if (digest(package) != marker['decision']['source_package_sha256']
            or package['metadata']['database_sha256'] != manifest['files']['parent.sqlite']
            or digest(marker['seed']) != fork.QUALIFIED_SEED
            or store.validate(target,test_key,replay=False)['world_sha256'] != report['world_sha256']
            or manifest['files']['database.sqlite'] != fork.QUALIFIED_DATABASE):
        raise ValueError('Qualifying archive does not extend the exact accepted source')
    with connect_read_only(target/'database.sqlite') as db:
        table = groups.table(db,'LIB:2028','GROUP:8')
        if table[0]['club'] != 'club:15' or table[0]['points'] != 10:
            raise ValueError('Verified Libertadores group outcome differs')
    return marker, digest(manifest['verification'])


def register(root, archive, test_key, old, *, test_only):
    signer = secrets.token_bytes(32)
    key_path = root/'commissioner.key'
    with tempfile.TemporaryDirectory(dir=root,prefix='.qualifying-source-') as temp:
        source=Path(temp)/'world'
        saved, verification_sha = verify_source(archive,test_key,old,source)
        with key_path.open('xb') as out:
            out.write(signer)
        registry=root/'authority/career.sqlite'
        seed=saved['seed']
        lineage.provision(registry,signer,test_only=test_only,commissioner='Lbragaa',
                          career_id=fork.QUALIFIED_CAREER,seed=seed,qualified_import=True)
        rules=policy(test_only)
        origin={'action':fork.QUALIFIED,'career':fork.QUALIFIED_CAREER,'profile':seasons.PROFILE,
                'test_only':test_only,'parent_checkpoint':fork.QUALIFIED_SOURCE,'source_checkpoint':fork.QUALIFIED_SOURCE,
                'archive_sha256':fork.QUALIFIED_ARCHIVE,'parent_sha256':fork.QUALIFIED_DATABASE,
                'seed_sha256':fork.QUALIFIED_SEED,'revealed_through':fork.QUALIFIED_CUTOFF,
                'source_entropy_parent':saved['decision']['source_entropy_parent'],'policy_sha256':digest(rules),
                'verified_replay_sha256':verification_sha}
        marker={'profile':seasons.PROFILE,'test_only':test_only,'acceptance_eligible':True,
                'decision':origin,'signature':lineage.sign(signer,origin),'seed':seed,'policy':rules}
        world=Path(temp)/'working'
        fork.initialize(source/'database.sqlite',world,marker,signer)
        with connect_read_only(world/'parent.sqlite') as before, connect_read_only(world/'database.sqlite') as after:
            baseline, imported = fingerprints(before), fingerprints(after)
            assert {k for k in baseline if baseline[k]!=imported[k]} <= {'ms_meta'}
        accepted=root/'accepted-qualifying'
        request_id=str(uuid5(NAMESPACE_URL,fork.QUALIFIED_ARCHIVE))
        head=seasons.stage_qualifying_import(registry,signer,world,accepted,request_id)
        template=seasons.acceptance_template(registry,signer,accepted)
        signed=lineage.signed(template,signer)
        assert seasons.accept_qualifying_import(registry,signer,accepted,signed)==head
        assert seasons.accept_qualifying_import(registry,signer,accepted,signed)==head
    portable=root/'qualifying-registered.zip'
    seasons.export(registry,signer,accepted,portable)
    restored=root/'verify-restore'
    proof=seasons.restore(registry,signer,portable,restored)
    assert proof['checkpoint']==head and proof['independent_restore']
    season_objects.remove_owned(restored,root)
    worker=bridge(root,old,registry,key_path,signer,test_only,career_id=fork.QUALIFIED_CAREER)
    with lineage.access(registry,signer) as (c,t):
        lineage.check_cursors(c,t,signer)
        info,_=seasons.current(c,t,signer)
        with connect_read_only(info['database']) as db:
            assert groups.table(db,'LIB:2028','GROUP:8')[0]['club']=='club:15'
            first_vasco=db.execute("""SELECT f.key,f.kickoff FROM ms_fixtures f JOIN ms_executions x ON x.fixture=f.key
                WHERE f.kickoff>? AND x.result_json IS NOT NULL AND 'club:15' IN (f.home,f.away)
                ORDER BY f.kickoff,f.key LIMIT 1""",(fork.QUALIFIED_CUTOFF,)).fetchone()
        assert c.execute('SELECT 1 FROM cursors WHERE fixture=?',(first_vasco['key'],)).fetchone() is None
        events=season_gameplay.next_events(c,info)
        assert events and events[0]['kind']=='narration'
    evidence={'career':fork.QUALIFIED_CAREER,'checkpoint':head,'clock':info['clock'],
              'first_vasco_narration_kickoff':first_vasco['kickoff'],'independent_restore':True,'test_only':test_only}
    lineage.publish_json(root/'verification.json',lineage.signed(evidence,signer))
    if test_only:
        from .test_qualifying_route import run
        run(root,worker,head,first_vasco['key'])
    print(json.dumps(evidence),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','archive','test-key','original-config'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--production',action='store_true')
    args=parser.parse_args()
    root=args.root.resolve(strict=True)
    if not root.is_dir() or any(root.iterdir()) or args.original_config.resolve().parent in (root,*root.parents):
        raise ValueError('Use a secured empty directory outside the old career')
    register(root,args.archive,args.test_key.read_bytes(),config(args.original_config),test_only=not args.production)
