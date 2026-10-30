"""Nonpromotable immediate-parent verification with explicit trusted attestation.

Parent sealing ALWAYS independently restores/replays a normal DEV package first.
Child verification authenticates that immutable parent and replays only its tail,
then compares every table, including historical records. This is a separate TEST
profile, not a cached verdict in the existing full-history verifier or an official
authority/acceptance route. A trusted key holder can forge attestations; this is
the same trusted-operator limitation as signatures, not distributed consensus.
"""
import hmac
import json
from pathlib import Path
import shutil
import tempfile
from ..checkpoints import staged_directory,read_json,write_json,manifest_for
from ..db import connect_read_only,file_sha256
from ..history import digest
from ..forward import sign
from ..seasons import fingerprints
from . import store

PROFILE='DEV-MULTISEASON-INCREMENTAL-1'
FILES={'parent.sqlite','database.sqlite','development.json'}
MAX_BYTES=2*1024**3


def _document(path,key,action):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>5*1024**2:raise ValueError('Invalid incremental metadata file')
    value=read_json(path)
    if set(value)!={'statement','signature'} or not isinstance(value['statement'],dict) or not isinstance(value['signature'],str):raise ValueError('Invalid incremental signature envelope')
    s=value['statement']
    if s.get('profile')!=PROFILE or s.get('action')!=action or s.get('test_only') is not True or s.get('acceptance_eligible') is not False:raise ValueError('Unsupported or promotable incremental profile')
    if not hmac.compare_digest(value['signature'],sign(key,s)):raise ValueError('Incremental signature differs')
    return s


def _hashes(directory):
    directory=Path(directory)
    if directory.is_symlink() or set(p.name for p in directory.iterdir())!=FILES:raise ValueError('Unexpected sealed snapshot inventory')
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):raise ValueError('Unsafe sealed snapshot')
    return {name:file_sha256(directory/name) for name in sorted(FILES)}


def authenticate_parent(directory,key):
    directory=Path(directory)
    if directory.is_symlink() or set(p.name for p in directory.iterdir())!={'snapshot','seal.json'}:raise ValueError('Unexpected sealed-parent inventory')
    s=_document(directory/'seal.json',key,'attest_fully_replayed_test_parent')
    if _hashes(directory/'snapshot')!=s.get('parent_files'):raise ValueError('Sealed parent bytes changed')
    if type(s.get('operations')) is not int or s['operations']<0 or s.get('full_parent_replay') is not True or s.get('verifier')!='full-ms-replay-attestation-1':raise ValueError('Missing or unsupported full parent verification attestation')
    store.authenticated(directory/'snapshot',key)
    return s


def seal_parent(package,destination,key):
    """The verifier produces the attestation itself; caller cannot supply a verdict."""
    with staged_directory(Path(destination)) as stage:
        report=store.restore(package,stage/'snapshot',key)
        if not report['independent_replay'] or report['acceptance_eligible']:raise ValueError('A fully replayed TEST parent is mandatory')
        with connect_read_only(stage/'snapshot/database.sqlite') as c:
            row=c.execute('SELECT sha256 FROM ms_operations ORDER BY sequence DESC LIMIT 1').fetchone()
        marker=read_json(stage/'snapshot/development.json')
        statement={'action':'attest_fully_replayed_test_parent','profile':PROFILE,'test_only':True,'acceptance_eligible':False,
                   'parent_files':_hashes(stage/'snapshot'),'operations':report['operations'],
                   'operation_head':row[0] if row else digest(marker['decision']),
                   'world_sha256':report['world_sha256'],'full_parent_replay':True,'verifier':'full-ms-replay-attestation-1'}
        write_json(stage/'seal.json',{'statement':statement,'signature':sign(key,statement)})
    return statement


def _copy_snapshot(source,target,expected):
    target.mkdir()
    for name in FILES:shutil.copyfile(Path(source)/name,target/name)
    if _hashes(target)!=expected:raise ValueError('Parent changed during snapshot copy')


def create(sealed_parent,destination,key):
    parent=authenticate_parent(sealed_parent,key)
    with staged_directory(Path(destination)) as stage:
        shutil.copytree(sealed_parent,stage/'parent')
        authenticate_parent(stage/'parent',key)
        _copy_snapshot(stage/'parent/snapshot',stage/'child',parent['parent_files'])
        statement={'action':'fork_incremental_test_child','profile':PROFILE,'test_only':True,'acceptance_eligible':False,
                   'parent_seal_sha256':file_sha256(stage/'parent/seal.json')}
        write_json(stage/'incremental.json',{'statement':statement,'signature':sign(key,statement)})
    return validate(destination,key)


def _authenticate(directory,key):
    directory=Path(directory)
    names={p.name for p in directory.iterdir()};base={'parent','child','incremental.json'}
    if names!=base and names!=base|{'manifest.json','verification.json'}:raise ValueError('Unexpected incremental package inventory')
    header=_document(directory/'incremental.json',key,'fork_incremental_test_child')
    if header.get('parent_seal_sha256')!=file_sha256(directory/'parent/seal.json'):raise ValueError('Incremental parent binding changed')
    parent=authenticate_parent(directory/'parent',key)
    child=directory/'child'
    if child.is_symlink() or not FILES<=set(p.name for p in child.iterdir()) or set(p.name for p in child.iterdir())-FILES-{'database.sqlite-journal','database.sqlite-wal','database.sqlite-shm'}:
        raise ValueError('Unexpected incremental child inventory')
    if any(p.is_symlink() or not p.is_file() for p in child.iterdir()):raise ValueError('Unsafe incremental child file')
    store.authenticated(directory/'child',key)
    for name in ('development.json','parent.sqlite'):
        if file_sha256(directory/'child'/name)!=parent['parent_files'][name]:raise ValueError('Child root/seed/migration differs from exact parent')
    return directory,parent


def _prefix(directory,parent):
    n=parent['operations']
    with connect_read_only(directory/'parent/snapshot/database.sqlite') as p,connect_read_only(directory/'child/database.sqlite') as c:
        old=[tuple(r) for r in p.execute('SELECT * FROM ms_operations ORDER BY sequence')]
        prefix=[tuple(r) for r in c.execute('SELECT * FROM ms_operations WHERE sequence<=? ORDER BY sequence',(n,))]
        if len(old)!=n or prefix!=old:raise ValueError('Authenticated historical operation prefix changed')
        if old and old[-1][-2]!=parent['operation_head']:raise ValueError('Parent operation-head commitment differs')
        return [dict(r) for r in c.execute('SELECT * FROM ms_operations WHERE sequence>? ORDER BY sequence',(n,))]


def run(directory,key,request_id,kind,args,*,crash=None):
    directory,parent=_authenticate(directory,key);_prefix(directory,parent)
    return store.run(directory/'child',key,request_id,kind,args,crash=crash)


def validate(directory,key,*,replay=True):
    directory,parent=_authenticate(directory,key);suffix=_prefix(directory,parent)
    report=store.validate(directory/'child',key,replay=False)
    if replay:
        with tempfile.TemporaryDirectory(dir=directory.parent,prefix='.incremental-replay-') as temp:
            target=Path(temp)/'child'
            _copy_snapshot(directory/'parent/snapshot',target,parent['parent_files'])
            for row in suffix:
                result=store.run(target,key,row['request_id'],row['kind'],json.loads(row['args_json']))
                if result!=json.loads(row['response_json']):raise ValueError('Independent incremental operation response differs')
            with connect_read_only(target/'database.sqlite') as c:
                if digest(fingerprints(c))!=report['world_sha256']:raise ValueError('Independent incremental world/history differs')
        authenticate_parent(directory/'parent',key)
        with connect_read_only(directory/'child/database.sqlite') as c:
            if digest(fingerprints(c))!=report['world_sha256']:raise ValueError('Child changed during verification')
    return {'profile':PROFILE,'test_only':True,'acceptance_eligible':False,'world_sha256':report['world_sha256'],
            'parent_world_sha256':parent['world_sha256'],'parent_attestation_authenticated':True,
            'parent_operations':parent['operations'],'replayed_operations':len(suffix),'independent_suffix_replay':replay}


def _bound(directory):
    files=list(Path(directory).rglob('*'))
    if any(p.is_symlink() for p in files) or sum(p.stat().st_size for p in files if p.is_file())>MAX_BYTES:raise ValueError('Unsafe or oversized incremental package')
    if set(p.name for p in (Path(directory)/'child').iterdir())!=FILES:raise ValueError('Only settled fixed-inventory child files may be exported')


def _copy_tree(source,target):
    shutil.copytree(Path(source)/'parent',target/'parent');shutil.copytree(Path(source)/'child',target/'child')
    shutil.copyfile(Path(source)/'incremental.json',target/'incremental.json')


def export(directory,destination,key):
    _bound(directory);before=validate(directory,key,replay=False)
    with staged_directory(Path(destination)) as stage:
        _copy_tree(directory,stage);report=validate(stage,key)
        if report!={**before,'independent_suffix_replay':True}:raise ValueError('Incremental child changed during export')
        write_json(stage/'verification.json',report);write_json(stage/'manifest.json',manifest_for(stage));_bound(stage)
    return report


def restore(package,destination,key):
    package=Path(package);_bound(package)
    if set(p.name for p in package.iterdir())!={'parent','child','incremental.json','manifest.json','verification.json'}:raise ValueError('Unexpected incremental archive inventory')
    if any((package/name).stat().st_size>5*1024**2 for name in ('manifest.json','verification.json')):raise ValueError('Oversized incremental metadata')
    if read_json(package/'manifest.json')!=manifest_for(package):raise ValueError('Incremental portable manifest differs')
    with staged_directory(Path(destination)) as stage:
        _copy_tree(package,stage);report=validate(stage,key)
        if report!=read_json(package/'verification.json'):raise ValueError('Independent incremental restoration differs')
    return report
