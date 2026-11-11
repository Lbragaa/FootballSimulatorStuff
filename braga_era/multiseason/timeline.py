"""Offline branching from authenticated accepted season history."""
from contextlib import closing
import hashlib
from pathlib import Path
import re
import json
import secrets
import sqlite3
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from .. import lineage, season_lineage, season_objects
from ..db import connect_read_only, file_sha256
from ..history import digest
from . import fork, store
from .registered import PROFILE, policy


def accepted_package(registry, signer, checkpoint):
    path = Path(registry).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        trusted = lineage.authority(db, signer)
        row = db.execute('SELECT path FROM accepted WHERE checkpoint=?', (checkpoint,)).fetchone()
        if not row:
            raise ValueError('Checkpoint is absent from the accepted registry')
        package, _ = season_lineage.authenticated_package(db, trusted, signer, row[0], require_head=False)
        return package, season_lineage.pool(db), trusted['seed'], trusted['career']


def accepted_history(registry, signer):
    """Return registered save identities without materializing football state."""
    path = Path(registry).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        trusted = lineage.authority(db, signer)
        result = []
        for row in db.execute('SELECT * FROM accepted ORDER BY generation DESC'):
            proof = json.loads(row['proof'])
            if proof['metadata']['profile'] != PROFILE:
                continue
            season_lineage.verify_node(proof, trusted, signer)
            meta = proof['metadata']
            if digest(meta) != row['checkpoint'] or meta['generation'] != row['generation']:
                raise ValueError('Accepted checkpoint index differs from signed proof')
            result.append({'checkpoint': row['checkpoint'], 'generation': meta['generation'],
                           'season': meta['season'], 'clock': meta['clock'],
                           'current': row['checkpoint'] == trusted['head'],
                           'descriptor_present': season_lineage.is_registered(row['path'])})
        return result


def bookmark(registry, signer, checkpoint, directory, name, *, description=''):
    """Publish a signed named reference in a separate savepoint directory."""
    if (not isinstance(name, str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,63}', name)
            or not isinstance(description, str) or len(description) > 500):
        raise ValueError('Use a short save name and description')
    directory = Path(directory).resolve(strict=True)
    if Path(registry).resolve().parent.parent in (directory, *directory.parents):
        raise ValueError('Use a savepoint directory outside the source authority')
    package, _, _, career = accepted_package(registry, signer, checkpoint)
    value = {'profile': 'timeline-bookmark-1', 'name': name, 'description': description, 'career': career,
             'checkpoint': checkpoint, 'clock': package['metadata']['clock'],
             'package_sha256': digest(package)}
    lineage.publish_json(directory / (name + '.json'), lineage.signed(value, signer))
    return value


def archive_rehearsal(world, test_key, verification, archive):
    """Compress the exact independently replayed TEST files and verify each member."""
    world, marker = store.authenticated(world, test_key)
    report = lineage.check_signed(verification, test_key)
    if marker['decision']['action'] != fork.REHEARSAL or report.get('verified') is not True:
        raise ValueError('A verified nonpromotable rehearsal is required')
    current = store.validate(world, test_key, replay=False)
    if (report.get('operation_count') != current['operations']
            or report.get('world_sha256') != current['world_sha256']):
        raise ValueError('The verification does not cover these exact world tables')
    archive = Path(archive).resolve()
    if archive.exists():
        raise FileExistsError(archive)
    names = ('database.sqlite', 'parent.sqlite', 'development.json')
    if set(p.name for p in world.iterdir()) != set(names):
        raise ValueError('Unexpected rehearsal file inventory')
    hashes = {name: file_sha256(world/name) for name in names}
    manifest = lineage.signed({'profile': 'timeline-rehearsal-archive-1', 'files': hashes,
                              'source_checkpoint': marker['decision']['source_checkpoint'],
                              'seed_sha256': marker['decision']['seed_sha256'],
                              'verification': verification}, test_key)
    with tempfile.TemporaryDirectory(dir=archive.parent, prefix='.timeline-archive-') as tmp:
        target = Path(tmp)/archive.name
        with ZipFile(target, 'x', compression=ZIP_DEFLATED, compresslevel=6) as out:
            out.writestr('archive.json', json.dumps(manifest, sort_keys=True))
            for name in names:
                out.write(world/name, name)
        with ZipFile(target) as check:
            if lineage.check_signed(json.loads(check.read('archive.json')), test_key) != manifest['document']:
                raise ValueError('Archived manifest differs')
            for name, expected in hashes.items():
                with check.open(name) as member:
                    if hashlib.file_digest(member, 'sha256').hexdigest() != expected:
                        raise ValueError('Archived rehearsal member differs')
        target.rename(archive)
    return file_sha256(archive)


def rehearse(registry, signer, checkpoint, destination, test_key, *, seed_mode, branch_seed=None):
    """Precommit a TEST branch without changing the accepted parent or registry."""
    if (seed_mode not in {'same', 'alternate'} or (seed_mode == 'same' and branch_seed is not None)
            or secrets.compare_digest(signer, test_key)):
        raise ValueError('Choose an explicit seed mode and a separate test signer')
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    if Path(registry).resolve().parent.parent in destination.parents:
        raise ValueError('Use a destination outside the source authority directory')
    package, pool, source_seed, career = accepted_package(registry, signer, checkpoint)
    state = package['state']['database.sqlite']
    chosen = source_seed if seed_mode == 'same' else branch_seed or secrets.token_hex(32)
    if seed_mode == 'alternate' and (not re.fullmatch('[0-9a-f]{64}', chosen) or chosen == source_seed):
        raise ValueError('Use a distinct explicit 256-bit seed for an alternate rehearsal')
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.timeline-source-') as temporary:
        source = Path(temporary) / 'database.sqlite'
        season_objects.materialize(pool, state, source)
        with connect_read_only(source) as db:
            meta = db.execute('SELECT parent_sha256,seed FROM ms_meta').fetchone()
            if meta['seed'] != source_seed:
                raise ValueError('Source seed differs from accepted authority')
            if db.execute("SELECT 1 FROM ms_fixtures WHERE status='claimed'").fetchone():
                raise ValueError('Cannot branch an unfinished match commitment')
        rules = policy(True)
        decision = {'action': fork.REHEARSAL, 'profile': PROFILE, 'test_only': True,
                    'parent_checkpoint': checkpoint, 'source_checkpoint': checkpoint,
                    'source_package_sha256': digest(package), 'source_career': career,
                    'parent_sha256': state['sha256'], 'source_entropy_parent': meta['parent_sha256'],
                    'policy_sha256': digest(rules), 'seed_mode': seed_mode, 'seed_sha256': digest(chosen)}
        marker = {'profile': PROFILE, 'test_only': True, 'acceptance_eligible': False,
                  'decision': decision, 'signature': lineage.sign(test_key, decision),
                  'seed': chosen, 'policy': rules}
        with lineage.staged_directory(destination) as staged:
            world = staged / 'world'
            fork.initialize(source, world, marker, test_key)
            store.validate(world, test_key)
    return decision
