"""Stable logical fingerprints independent of SQLite page layout."""
import hashlib
from importlib.resources import files
import json
import heapq
from contextlib import ExitStack
from pathlib import Path
import tempfile

# JSONEncoder.encode creates fresh per-call traversal state. Reuse only its
# immutable options, never serialized values or successful validation results.
_CANONICAL_ENCODER = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False)

def canonical_json(value) -> str:
    return _CANONICAL_ENCODER.encode(value)


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_fingerprint(connection, name: str) -> dict:
    cursor = connection.execute(f"SELECT * FROM {quote_identifier(name)}")
    columns = [column[0] for column in cursor.description]
    # Preserve the frozen contract: these are sorted JSON STRING rows inside a
    # second canonical JSON object, not an array of raw SQLite values. Avoid
    # allocating that entire doubly escaped object for growing career tables.
    with ExitStack() as temporary:
        root=None;runs=[];batch=[];size=0;count=0;serial=0
        def spill(values):
            nonlocal serial,root
            if root is None:root=Path(temporary.enter_context(tempfile.TemporaryDirectory(prefix='braga-fingerprint-')))
            path=root/str(serial);serial+=1
            with path.open('w',encoding='utf-8',newline='\n') as stream:
                for value in values:stream.write(value+'\n')
            return path
        def merged(paths):
            with ExitStack() as opened:
                streams=[opened.enter_context(p.open(encoding='utf-8',newline='\n')) for p in paths]
                yield from heapq.merge(*(map(lambda line:line.removesuffix('\n'),s) for s in streams))
        for row in cursor:
            value=canonical_json(list(row));batch.append(value);count+=1;size+=len(value.encode('utf-8'))
            if size>=FINGERPRINT_CHUNK_BYTES or len(batch)>=FINGERPRINT_CHUNK_ROWS:
                runs.append(spill(sorted(batch)));batch=[];size=0
        if runs:
            if batch:runs.append(spill(sorted(batch)))
            # Bound both memory and file descriptors, including very large tables.
            while len(runs)>FINGERPRINT_FAN_IN:
                following=[]
                for i in range(0,len(runs),FINGERPRINT_FAN_IN):
                    group=runs[i:i+FINGERPRINT_FAN_IN];following.append(spill(merged(group)))
                    for path in group:path.unlink()
                runs=following
            rows=merged(runs)
        else:rows=iter(sorted(batch))
        sha=hashlib.sha256(b'{"columns":'+canonical_json(columns).encode('utf-8')+b',"rows":[')
        try:
            for i,value in enumerate(rows):
                if i:sha.update(b',')
                sha.update(canonical_json(value).encode('utf-8'))
        finally:
            if hasattr(rows,'close'):rows.close()
        sha.update(b']}')
        return {'rows':count,'sha256':sha.hexdigest()}


FINGERPRINT_CHUNK_BYTES=8*1024**2
FINGERPRINT_CHUNK_ROWS=50000
FINGERPRINT_FAN_IN=32


def completed_fixtures(connection) -> list[dict]:
    return [dict(row) for row in connection.execute(
        "SELECT * FROM fixtures WHERE status='final' ORDER BY id")]


def load_baseline() -> dict:
    return json.loads(files("braga_era").joinpath("baselines/save046.json").read_text(encoding="utf-8"))
