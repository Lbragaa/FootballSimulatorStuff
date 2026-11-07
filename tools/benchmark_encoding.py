"""Paired deterministic CPU benchmark; no private inputs or outcome changes."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.history import canonical_json, digest


def run(iterations=50000):
    rows = [{"key": str(i), "score": [i%4,i%3], "details": {"name": "São Paulo", "nullable": None}} for i in range(20)]
    old = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert all(old(v) == canonical_json(v) for v in rows)
    measurements = {"before": [], "after": []}
    for trial in range(6):
        order = [("before", old), ("after", canonical_json)]
        if trial%2: order.reverse()
        for name, function in order:
            start = time.process_time()
            for i in range(iterations): function(rows[i%len(rows)])
            measurements[name].append(time.process_time()-start)
    before, after = (statistics.median(measurements[n]) for n in ("before","after"))
    return {"benchmark":"canonical-encoder-options-reuse-1", "iterations_per_trial":iterations,
            "paired_cpu_seconds":measurements, "before_median_cpu_seconds":before,
            "after_median_cpu_seconds":after,"speedup":before/after,
            "exact_bytes_equal":True,"input_sha256":digest(rows),
            "scope":"synthetic serialization microbenchmark; not whole-episode speedup"}


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); r=run(); a.output.write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps(r))
