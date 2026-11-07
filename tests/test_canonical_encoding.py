"""Byte equivalence matters: these bytes commit every historic seed/signature."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import pytest
from braga_era.history import canonical_json


def reference(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def test_encoder_exact_bytes_and_thread_isolation():
    values = [None, True, 123, -0.0, 1e-20, 'São Paulo "\\\n',
              {"z": [1, {"á": None}], "a": {2: "int key"}},
              [dict(id=i, score=[i%5, i%3], name="Vasco", nullable=None) for i in range(100)]]
    with ThreadPoolExecutor(4) as pool:
        assert list(pool.map(canonical_json, values*100)) == [reference(v) for v in values*100]
    obj = {"a": [1]}
    canonical_json(obj)
    obj["a"].append(2)
    assert canonical_json(obj) == '{"a":[1,2]}'  # No object/value cache.


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan, object()])
def test_rejects_same_unsupported_values(value):
    with pytest.raises((ValueError, TypeError)):
        canonical_json(value)
    with pytest.raises((ValueError, TypeError)):
        reference(value)


def test_cycle_failure_does_not_poison_next_call():
    obj = []; obj.append(obj)
    with pytest.raises(ValueError): canonical_json(obj)
    assert canonical_json({"ok": True}) == reference({"ok": True})


@pytest.mark.parametrize('external',[False,True])
def test_table_fingerprint_keeps_double_encoded_sort_contract(external,monkeypatch,tmp_path):
    import hashlib
    import sqlite3
    import tempfile
    from braga_era import history
    if external:
        monkeypatch.setattr(history,'FINGERPRINT_CHUNK_BYTES',16)
        monkeypatch.setattr(history,'FINGERPRINT_FAN_IN',2)
    monkeypatch.setattr(tempfile,'tempdir',str(tmp_path))
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE "odd name"("z quoted" TEXT,n REAL,empty TEXT)')
    values=[('São Paulo "\\\n\t😀',-0.0,None),('a\u2028b',1e-20,'')] + [(str(i%13),float(i%17),None) for i in range(100)]
    c.executemany('INSERT INTO "odd name" VALUES(?,?,?)',values)
    columns=['z quoted','n','empty']
    rows=sorted(reference(list(r)) for r in c.execute('SELECT * FROM "odd name"'))
    expected=hashlib.sha256(reference({'columns':columns,'rows':rows}).encode('utf-8')).hexdigest()
    assert history.table_fingerprint(c,'odd name')=={'rows':len(rows),'sha256':expected}
    c.execute('DELETE FROM "odd name"')
    expected=hashlib.sha256(reference({'columns':columns,'rows':[]}).encode('utf-8')).hexdigest()
    assert history.table_fingerprint(c,'odd name')=={'rows':0,'sha256':expected}
    assert not list(tmp_path.glob('braga-fingerprint-*'))
    c.close()
