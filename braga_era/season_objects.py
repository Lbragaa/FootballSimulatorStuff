"""Bounded immutable chunks shared by registered season checkpoints."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile

CHUNK = 65536
MAX_FILE = 2 * 1024**3
MAX_OBJECT = 16 * 1024**2
HASH = re.compile(r'[0-9a-f]{64}\Z')


def remove_owned(path,parent):
    """Windows/cloud readonly cleanup, restricted to an explicitly owned child."""
    import os
    import stat
    import shutil
    path=Path(path);parent=Path(parent).resolve()
    if path.is_symlink() or path.resolve()!=parent/path.name:raise ValueError('Redirected owned directory')
    target=path.resolve()
    if not target.exists():return
    for item in [target,*target.rglob('*')]:
        resolved=item.resolve()
        if item.is_symlink() or resolved!=target and target not in resolved.parents:raise ValueError('Unsafe owned cleanup entry')
        os.chmod(item,stat.S_IRWXU)
    shutil.rmtree(target)


def put(pool, data):
    if len(data)>MAX_OBJECT:raise ValueError('Season object exceeds bound')
    pool=Path(pool);pool.mkdir(parents=True,exist_ok=True)
    identity=hashlib.sha256(data).hexdigest();target=pool/(identity+'.gz')
    if target.exists():
        if get(pool,identity)!=data:raise ValueError('Season object changed')
        return identity
    with tempfile.NamedTemporaryFile(dir=pool,delete=False) as stream:
        temporary=Path(stream.name)
        stream.write(gzip.compress(data,mtime=0))
        stream.flush()
        import os
        os.fsync(stream.fileno())
    try:
        # Authority writer lock serializes publication; no accepted blob is replaced.
        if target.exists():
            if get(pool,identity)!=data:raise ValueError('Season object changed')
        else:temporary.rename(target)
    finally:temporary.unlink(missing_ok=True)
    return identity


def get(pool, identity):
    if not isinstance(identity,str) or not HASH.fullmatch(identity):raise ValueError('Invalid season object identity')
    path=Path(pool)/(identity+'.gz')
    if path.is_symlink() or path.stat().st_size>MAX_OBJECT*2:raise ValueError('Unsafe season object')
    with gzip.open(path,'rb') as stream:data=stream.read(MAX_OBJECT+1)
    if len(data)>MAX_OBJECT or hashlib.sha256(data).hexdigest()!=identity:raise ValueError('Corrupted season object')
    return data


def capture(pool, path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_FILE:raise ValueError('Unsafe season file')
    sha=hashlib.sha256();pages=[];size=0
    with path.open('rb') as stream:
        while data:=stream.read(CHUNK):
            sha.update(data);size+=len(data);pages.append(put(pool,data))
    from .history import canonical_json
    level=0
    nodes=[put(pool,canonical_json({'kind':'season-page-index-1','level':0,'children':pages[i:i+64]}).encode())
           for i in range(0,len(pages),64)]
    if not nodes:nodes=[put(pool,canonical_json({'kind':'season-page-index-1','level':0,'children':[]}).encode())]
    while len(nodes)>1:
        level+=1
        nodes=[put(pool,canonical_json({'kind':'season-page-index-1','level':level,'children':nodes[i:i+64]}).encode())
               for i in range(0,len(nodes),64)]
    return {'bytes':size,'sha256':sha.hexdigest(),'index':nodes[0]}


def pages(pool,descriptor):
    if 'pages' in descriptor:
        yield from descriptor['pages'];return  # original profile-3 TEST packages remain readable.
    count=0;maximum=(descriptor['bytes']+CHUNK-1)//CHUNK
    def walk(identity,expected=None):
        nonlocal count
        node=json.loads(get(pool,identity))
        if (set(node)!={'kind','level','children'} or node['kind']!='season-page-index-1'
            or type(node['level']) is not int or not 0<=node['level']<=4 or expected is not None and node['level']!=expected
            or not isinstance(node['children'],list) or len(node['children'])>64):raise ValueError('Invalid season page index')
        for child in node['children']:
            if node['level']:yield from walk(child,node['level']-1)
            else:
                count+=1
                if count>maximum:raise ValueError('Season page index exceeds file bound')
                yield child
    yield from walk(descriptor['index'])
    if count!=maximum:raise ValueError('Season page index is incomplete')


def materialize(pool, descriptor, path):
    if (set(descriptor) not in ({'bytes','sha256','pages'},{'bytes','sha256','index'}) or type(descriptor['bytes']) is not int
        or not 0<=descriptor['bytes']<=MAX_FILE or not HASH.fullmatch(descriptor['sha256'])
        or 'pages' in descriptor and len(descriptor['pages'])!=(descriptor['bytes']+CHUNK-1)//CHUNK):
        raise ValueError('Invalid season file descriptor')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    from .db import file_sha256
    if path.exists():
        if path.is_symlink() or path.stat().st_size!=descriptor['bytes'] or file_sha256(path)!=descriptor['sha256']:
            raise ValueError('Materialized season cache changed')
        # Exact signed file bytes authenticate this materialized parent, rather
        # than a cached boolean verdict. Fresh restoration reads every chunk.
        return
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name);sha=hashlib.sha256();size=0
        try:
            for i,page in enumerate(pages(pool,descriptor)):
                data=get(pool,page)
                expected=min(CHUNK,descriptor['bytes']-i*CHUNK)
                if len(data)!=expected:raise ValueError('Invalid season chunk length')
                stream.write(data);sha.update(data);size+=len(data)
        except BaseException:
            stream.close();temporary.unlink(missing_ok=True);raise
    try:
        if size!=descriptor['bytes'] or sha.hexdigest()!=descriptor['sha256']:raise ValueError('Season file hash differs')
        temporary.rename(path)
    finally:temporary.unlink(missing_ok=True)
