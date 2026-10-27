"""Guarded scratch access, crash-released process locks, transactional before/after journal."""

from contextlib import contextmanager, closing
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import sqlite3
from ..acceptance import catalog
from ..checkpoints import staged_directory, write_json, read_json
from ..db import connect_read_only, file_sha256
from ..history import canonical_json as encode, digest, table_fingerprint
from ..migrations import rows_by_key, diff
from . import SCOPE, VERSION
from .scope import current as current_scope
from .policy import is_readiness, WorldPolicy, ReadinessPolicy, load_policy
from . import forward_schema
from .schema import DDL, TABLES

MUTABLE_LEGACY = {
    "fixtures",
    "clubs",
    "libertadores_2027_round_of_16",
    "sudamericana_2027_playoffs",
    "cdb_2027_bracket",
    "cdb_2027_legs",
    "finance_ledger",
    "payroll_periods",
    "payroll_obligations",
}


def tables(c):
    return [
        r[0]
        for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def captured(c):
    return {
        t: rows_by_key(c, t)
        for t in tables(c)
        if t in MUTABLE_LEGACY
        or t in (TABLES | forward_schema.TABLES) - {"world_operations", "world_cursors"}
    }


def journal(c, phase, before):
    after = captured(c)
    previous = c.execute(
        "SELECT sha256 FROM world_operations ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    previous = previous[0] if previous else "0" * 64
    for op in diff(before, after):
        item = {
            "phase": phase,
            "table": op["table"],
            "key": op["key"],
            "before": (
                forward_schema.pack(c, op["before"])
                if forward_schema.enabled(c)
                else op["before"]
            ),
            "after": (
                forward_schema.pack(c, op["after"])
                if forward_schema.enabled(c)
                else op["after"]
            ),
            "previous_sha256": previous,
        }
        hashed = digest(item)
        c.execute(
            "INSERT INTO world_operations(phase,table_name,row_key_json,before_json,after_json,previous_sha256,sha256) VALUES(?,?,?,?,?,?,?)",
            (
                phase,
                op["table"],
                encode(op["key"]),
                encode(item["before"]) if item["before"] is not None else None,
                encode(item["after"]) if item["after"] is not None else None,
                previous,
                hashed,
            ),
        )
        previous = hashed


@contextmanager
def transaction(c, phase):
    c.execute("BEGIN IMMEDIATE")
    before = captured(c)
    try:
        yield
        journal(c, phase, before)
        c.commit()
    except BaseException:
        c.rollback()
        raise


@contextmanager
def process_lock(directory, name=".runner.lock"):
    if Path(name).name != name or name in ("", ".", ".."):
        raise ValueError("Process lock name must be a local filename")
    path = Path(directory) / name
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Another world runner owns the process lock") from error
        try:
            yield stream
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def authenticate(directory):
    directory = Path(directory).resolve()
    marker = read_json(directory / "world.json")
    if marker != {
        "scope": current_scope(),
        "version": VERSION,
        "parent_sha256": catalog()["database_sha256"],
        "promotable": False,
    }:
        raise ValueError("Not a registered, nonpromotable development world")
    if file_sha256(directory / "parent.sqlite") != catalog()["database_sha256"]:
        raise ValueError("Accepted parent hash mismatch")
    if (directory / "database.sqlite").samefile(directory / "parent.sqlite"):
        raise ValueError("Working DB must not alias its immutable parent")
    return directory


@contextmanager
def writer(directory):
    directory = authenticate(directory)
    with process_lock(directory), closing(
        sqlite3.connect(directory / "database.sqlite", timeout=0, isolation_level=None)
    ) as c:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA synchronous=FULL")
        info = c.execute("SELECT * FROM world_info").fetchone()
        if (
            info["scope"] != current_scope()
            or info["version"] != VERSION
            or info["parent_sha256"] != catalog()["database_sha256"]
        ):
            raise ValueError("Unsupported world identity/profile")
        policy = load_policy(json.loads(info["policy_json"]))
        policy.validate()
        yield c, policy


def create(parent, destination, seed, policy=None):
    parent = Path(parent).resolve()
    policy = policy or WorldPolicy()
    policy.validate()
    if file_sha256(parent) != catalog()["database_sha256"]:
        raise ValueError("World creation requires the exact accepted 046C v2 parent")
    with staged_directory(Path(destination)) as stage:
        shutil.copyfile(parent, stage / "parent.sqlite")
        shutil.copyfile(parent, stage / "database.sqlite")
        marker = {
            "scope": current_scope(),
            "version": VERSION,
            "parent_sha256": catalog()["database_sha256"],
            "promotable": False,
        }
        write_json(stage / "world.json", marker)
        # Initialization seed/policy are persisted before generating a single modeled-player draw.
        write_json(
            stage / "initialization_commitment.json",
            {
                "seed": str(seed),
                "policy": asdict(policy),
                "parent_sha256": marker["parent_sha256"],
            },
        )
        with closing(
            sqlite3.connect(stage / "database.sqlite", isolation_level=None)
        ) as c:
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys=ON")
            before = captured(c)
            c.executescript(
                "BEGIN IMMEDIATE;\n"
                + DDL
                + (forward_schema.DDL if is_readiness(policy) else "")
            )
            try:
                now = c.execute(
                    "SELECT value FROM meta WHERE key='current_date'"
                ).fetchone()[0]
                c.execute(
                    "INSERT INTO world_info VALUES(1,?,?,?,?,?,?)",
                    (
                        current_scope(),
                        VERSION,
                        marker["parent_sha256"],
                        encode(asdict(policy)),
                        str(seed),
                        now,
                    ),
                )
                from . import rosters, adapters

                rosters.install(
                    c, WorldPolicy() if is_readiness(policy) else policy, now
                )
                adapters.install(c)
                import calendar

                for month in range(9, 13):
                    period = f"2027-{month:02}"
                    c.execute(
                        "INSERT INTO world_obligations VALUES(?,?,?,?)",
                        (
                            "payroll:" + period,
                            f"{period}-{calendar.monthrange(2027,month)[1]} 23:59",
                            "scheduled",
                            encode({"policy": "incremental_actual_days_month_end_v1"}),
                        ),
                    )
                journal(c, "initialize", before)
                c.commit()
            except BaseException:
                c.rollback()
                raise
        from .audit import audit

        with connect_read_only(stage / "database.sqlite") as c:
            audit(c, stage / "parent.sqlite")
        if file_sha256(parent) != marker["parent_sha256"]:
            raise ValueError("Accepted source changed during initialization")
    return {
        "scope": current_scope(),
        "directory": str(Path(destination).resolve()),
        "promotable": False,
    }


def logical_hash(c):
    # Pending sealed results are not part of another match's pre-kickoff football state.
    return digest(
        {
            t: table_fingerprint(c, t)
            for t in tables(c)
            if t
            not in (
                "world_operations",
                "world_blobs",
                "world_cursors",
                "world_executions",
                "world_batches",
            )
        }
    )
