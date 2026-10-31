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
