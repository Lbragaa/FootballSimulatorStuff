"""Restore missing legacy head database members from its exact signed archive.

Run with the worker stopped and an explicitly approved checkpoint. The default
stages and verifies the repair only. Publication never replaces an existing file.
"""

import argparse
import json
from pathlib import Path
import tempfile

from braga_era import lineage
from braga_era.bridge.__main__ import config
from braga_era.checkpoints import _publish_file
from braga_era.db import file_sha256
from tools.preflight_live_career import snapshot


def prepare(db, trusted, key, checkpoint, stage):
    if trusted["head"] != checkpoint:
        raise ValueError("Expected accepted head changed")
    row = db.execute("SELECT path FROM accepted WHERE checkpoint=?", (checkpoint,)).fetchone()
    if not row:
        raise ValueError("An accepted legacy successor is required")
    parent = Path(row["path"])
    info, missing = lineage.stage_legacy_parent(db, trusted, key, parent, stage)
    return parent, info, missing


def publish(db, trusted, key, checkpoint):
    row = db.execute("SELECT path FROM accepted WHERE checkpoint=?", (checkpoint,)).fetchone()
    if trusted["head"] != checkpoint or not row:
        raise ValueError("Expected accepted head changed")
    parent = Path(row["path"])
    # Same volume for no-replace publication. An interrupted repair can retry
    # from the same signed archive and check the members already restored.
    with tempfile.TemporaryDirectory(dir=parent, prefix=".repair-") as stage:
        parent, info, missing = prepare(db, trusted, key, checkpoint, stage)
        payload = parent / "payload"
        manifest = lineage.read_json(info["payload"] / "manifest.json")["files"]
        for name in missing:
            staged_file = info["payload"] / name
            if file_sha256(staged_file) != manifest[name]:
                raise ValueError("Staged accepted member bytes differ")
            _publish_file(staged_file, payload / name)
        lineage.parent_info(db, trusted, key, parent)
    return missing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--scratch", required=True, type=Path, help="Existing disposable scratch directory")
    parser.add_argument("--apply-approved-repair", action="store_true")
    args = parser.parse_args()
    v = config(args.config)
    key = Path(v["key_file"]).read_bytes()
    scratch = args.scratch.resolve(strict=True)
    tempfile.tempdir = str(scratch)
    if args.apply_approved_repair:
        with lineage.access(v["registry"], key, lock=True) as (db, trusted):
            missing = publish(db, trusted, key, args.expected_head)
    else:
        with snapshot(v["registry"]) as db, tempfile.TemporaryDirectory(dir=scratch) as stage:
            trusted = lineage.authority(db, key)
            _, _, missing = prepare(db, trusted, key, args.expected_head, stage)
    print(json.dumps({"checkpoint": args.expected_head, "verified_members": missing,
                      "published": args.apply_approved_repair}))
