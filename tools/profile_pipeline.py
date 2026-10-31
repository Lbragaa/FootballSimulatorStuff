"""Profile a fixed, isolated DEV world through independent restore. No transport.

Only exact accepted root input is supported; no production registry/key/config is
loaded. Output contains counts/timings/function names, never scores or raw SQL.
This is a baseline for the DEV pipeline, not a measured live-episode speedup.
"""
import argparse
from collections import Counter
import cProfile
import json
from pathlib import Path
import pstats
import sqlite3
import sys
import time
import tempfile
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.seasons import AcceptedSource
from braga_era.world.storage import create
from braga_era.world.runner import advance
from braga_era.world.policy import ReadinessPolicy
from braga_era.world.packages import export_world, fingerprints
from braga_era.checkpoints import restore_checkpoint


def run(database, output):
    source = AcceptedSource.root(database)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    temporary_root = output / "temporary"
    temporary_root.mkdir()
    original_tempdir = tempfile.tempdir
    world, archive, restored = output / "world", output / "PRIVATE-NONCANONICAL.zip", output / "restored"
    stages, counts, stage_queries = {}, Counter(), {}
    original_connect = sqlite3.connect

    class MeteredConnection(sqlite3.Connection):
        def execute(self, sql, parameters=(), /):
            counts[str(sql).split(None, 1)[0].upper()] += 1
            return super().execute(sql, parameters)

        def executemany(self, sql, parameters, /):
            counts["EXECUTEMANY"] += 1
            return super().executemany(sql, parameters)

    def connect(*args, **kwargs):
        kwargs.setdefault("factory", MeteredConnection)
        return original_connect(*args, **kwargs)

    def measure(name, function, *args, **kwargs):
        wall, cpu, before = time.perf_counter(), time.process_time(), counts.copy()
        value = function(*args, **kwargs)
        stages[name] = {"wall_seconds": round(time.perf_counter()-wall, 6),
                        "cpu_seconds": round(time.process_time()-cpu, 6)}
        stage_queries[name] = dict(counts-before)
        return value

    profiler = cProfile.Profile()
    tracemalloc.start()
    sqlite3.connect = connect  # development process only; restored even on failure.
    tempfile.tempdir = str(temporary_root)  # avoid inaccessible sandbox system TEMP.
    try:
        profiler.enable()
        measure("world_initialization", create, source.database, world, "multiseason-profile-fixed-v1", ReadinessPolicy())
        measure("first_simultaneous_group_including_audits", advance, world,
                until="2027-09-30 23:59", max_groups=1)
        measure("export_including_independent_validation", export_world, world, archive)
        measure("independent_restoration", restore_checkpoint, archive, restored)
        with connect_read_only(world / "database.sqlite") as c:
            expected = fingerprints(c)
            fixtures = c.execute("SELECT count(*) FROM world_receipts").fetchone()[0]
        with connect_read_only(restored / "database.sqlite") as c:
            if fingerprints(c) != expected:
                raise ValueError("Independent restored state mismatch")
        profiler.disable()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        sqlite3.connect = original_connect
        tempfile.tempdir = original_tempdir
        tracemalloc.stop()
        profiler.disable()
    stats = pstats.Stats(profiler)
    root = Path(__file__).resolve().parents[1]
    functions = []
    for (filename, line, name), (cc, nc, tt, ct, callers) in stats.stats.items():
        path = Path(filename)
        if path.is_absolute() and path.is_relative_to(root) and "braga_era" in path.parts:
            functions.append({"function": f"{path.relative_to(root).as_posix()}:{line}:{name}",
                              "calls": nc, "self_seconds": round(tt, 6), "cumulative_seconds": round(ct, 6)})
    report = {"scope": "NONCANONICAL DEVELOPMENT TEST", "benchmark": "dev-first-group-1",
              "parent_sha256": source.database_sha256, "seed_policy": "fixed-before-results",
              "stages": stages, "sqlite_execute_calls": dict(counts), "queries_by_stage": stage_queries,
              "top_functions": sorted(functions, key=lambda x: -x["cumulative_seconds"])[:25],
              "python_peak_traced_bytes": peak, "archive_bytes": archive.stat().st_size,
              "world_database_bytes": (world / "database.sqlite").stat().st_size,
              "fixtures": fixtures, "world_sha256": digest(expected), "restored_equivalent": True,
              "original_unchanged": file_sha256(source.database) == source.database_sha256,
              "limits": ["cProfile/tracemalloc add overhead; not a live episode latency measurement",
                         "execute call counts include PRAGMA/control statements and exclude direct cursor calls",
                         "no OS disk-I/O counters; memory measures Python allocations only",
                         "no GitHub polling, authority acceptance or narration in this DEV baseline"]}
    (output / "benchmark.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.db, args.output)
    print(json.dumps({k: report[k] for k in ("benchmark", "stages", "fixtures", "restored_equivalent", "original_unchanged")}))
