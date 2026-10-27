"""Portable, nonpromotable world checkpoints with exact-parent and deterministic replay verification."""

from dataclasses import asdict
import json
from pathlib import Path
import shutil
import tempfile
from ..checkpoints import (
    staged_directory,
    manifest_for,
    write_json,
    read_json,
    export_checkpoint,
)
from ..db import connect_read_only, file_sha256
from ..history import digest, table_fingerprint
from . import SCOPE, VERSION
from .audit import audit
from .storage import authenticate, writer, create, tables
from .runner import advance, pending

FILES = {
    "database.sqlite",
    "parent.sqlite",
    "world.json",
    "initialization_commitment.json",
    "checkpoint.json",
    "validation.json",
    "operations.json",
    "private_matches.json",
    "narration.json",
    "rosters.json",
}


def fingerprints(c):
    return {t: table_fingerprint(c, t) for t in tables(c) if t != "world_cursors"}


def verify_directory(directory, *, replay=True):
    directory = authenticate(directory)
    if read_json(directory / "manifest.json") != manifest_for(directory):
        raise ValueError("Development checkpoint manifest mismatch")
    if set(read_json(directory / "manifest.json")["files"]) != FILES:
        raise ValueError("Unexpected development payload inventory")
    metadata = read_json(directory / "checkpoint.json")
    if (
        metadata.get("save_version") != "DEV-03B"
        or metadata.get("scope") != SCOPE
        or metadata.get("promotable") is not False
    ):
        raise ValueError("Development package cannot claim canonical identity")
    with connect_read_only(directory / "database.sqlite") as c:
        report = audit(c, directory / "parent.sqlite")
        if pending(c):
            raise ValueError("Cannot export/verify an incomplete execution batch")
        info = dict(c.execute("SELECT * FROM world_info").fetchone())
        expected = fingerprints(c)
        if metadata != {
            "format_version": 1,
            "save_version": "DEV-03B",
            "scope": SCOPE,
            "promotable": False,
            "version": VERSION,
            "parent_sha256": info["parent_sha256"],
            "database_sha256": file_sha256(directory / "database.sqlite"),
            "clock": info["clock"],
            "world_sha256": digest(expected),
            "policy_sha256": digest(json.loads(info["policy_json"])),
        }:
            raise ValueError("Development metadata differs from verified database")
        if read_json(directory / "validation.json") != report:
            raise ValueError("Stored audit differs")
        operations = [
            dict(r)
            for r in c.execute("SELECT * FROM world_operations ORDER BY sequence")
        ]
        matches = [
            dict(r)
            for r in c.execute("SELECT * FROM world_executions ORDER BY fixture_key")
        ]
        narration = [
            dict(r)
            for r in c.execute("SELECT * FROM world_cursors ORDER BY fixture_key")
        ]
        from .rosters import distribution

        for filename, value in [
            ("operations.json", operations),
            ("private_matches.json", matches),
            ("narration.json", narration),
            ("rosters.json", distribution(c)),
        ]:
            if read_json(directory / filename) != value:
                raise ValueError("Export does not match database: " + filename)
        commitment = read_json(directory / "initialization_commitment.json")
        if commitment != {
            "seed": info["seed"],
            "policy": json.loads(info["policy_json"]),
            "parent_sha256": info["parent_sha256"],
        }:
            raise ValueError("Initialization commitment differs")
        receipts = {
            r["fixture_key"]
            for r in c.execute("SELECT fixture_key FROM world_receipts")
        }
        for cursor in narration:
            row = c.execute(
                "SELECT * FROM world_executions WHERE fixture_key=?",
                (cursor["fixture_key"],),
            ).fetchone()
            if (
                cursor["fixture_key"] not in receipts
                or cursor["result_sha256"] != row["result_sha256"]
                or not 0
                <= cursor["sequence"]
                <= len(json.loads(row["result_json"])["events"])
            ):
                raise ValueError("Invalid portable narration cursor")
    if replay:
        # A re-sealed manifest or journal is not authority: replay the entire bounded world from exact parent/seed.
        with tempfile.TemporaryDirectory(
            dir=directory.parent, prefix=".world-replay-"
        ) as scratch:
            target = Path(scratch) / "replay"
            create(directory / "parent.sqlite", target, info["seed"])
            if receipts:
                advance(target, until=info["clock"])
            with connect_read_only(target / "database.sqlite") as c:
                if fingerprints(c) != expected:
                    raise ValueError(
                        "Independent world replay differs from exported state"
                    )
    return {
        "ok": True,
        "metadata": metadata,
        "validation": report,
        "acceptance_eligible": False,
        "independent_replay": replay,
    }


def export_world(directory, archive):
    directory = authenticate(directory)
    archive = Path(archive)
    archive.resolve().parent.mkdir(parents=True, exist_ok=True)
    # Freeze under the same crash-released lock as execution/narration. Never package a live transaction.
    with tempfile.TemporaryDirectory(
        dir=archive.resolve().parent, prefix=".world-package-"
    ) as scratch:
        stage = Path(scratch)
        with writer(directory) as (c, policy):
            report = audit(c, directory / "parent.sqlite")
            if pending(c):
                raise ValueError("Resume the committed batch before exporting")
            for filename in (
                "database.sqlite",
                "parent.sqlite",
                "world.json",
                "initialization_commitment.json",
            ):
                shutil.copyfile(directory / filename, stage / filename)
            info = c.execute("SELECT * FROM world_info").fetchone()
            metadata = {
                "format_version": 1,
                "save_version": "DEV-03B",
                "scope": SCOPE,
                "promotable": False,
                "version": VERSION,
                "parent_sha256": info["parent_sha256"],
                "database_sha256": file_sha256(stage / "database.sqlite"),
                "clock": info["clock"],
                "world_sha256": digest(fingerprints(c)),
                "policy_sha256": policy.fingerprint,
            }
            write_json(stage / "checkpoint.json", metadata)
            write_json(stage / "validation.json", report)
            from .rosters import distribution

            for filename, query in [
                ("operations.json", "SELECT * FROM world_operations ORDER BY sequence"),
                (
                    "private_matches.json",
                    "SELECT * FROM world_executions ORDER BY fixture_key",
                ),
                ("narration.json", "SELECT * FROM world_cursors ORDER BY fixture_key"),
            ]:
                write_json(stage / filename, [dict(r) for r in c.execute(query)])
            write_json(stage / "rosters.json", distribution(c))
        write_json(stage / "manifest.json", manifest_for(stage))
        return export_checkpoint(stage, archive)
