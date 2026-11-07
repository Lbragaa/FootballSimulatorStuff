"""Authenticate a legacy career without opening its databases for writing.

Only counts and checkpoint identity leave this process. The extracted head and
its independent replay are temporary, including when verification fails.
"""

import argparse
from contextlib import closing, contextmanager
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import tempfile
from zipfile import ZipFile

from braga_era import lineage, season_authority
from braga_era.bridge.__main__ import config
from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN_PROFILE
from braga_era.bridge.control import Controls, OPERATIONS, PROFILE as CONTROL_PROFILE
from braga_era.bridge.worker import check as check_ledger
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import canonical_json, digest


@contextmanager
def snapshot(path):
    uri = Path(path).resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        yield db


def inventory(folder, proof):
    archive = folder / "checkpoint.zip"
    if archive.is_symlink() or file_sha256(archive) != proof["package_sha256"]:
        raise ValueError("Accepted archive bytes do not match the signed proof")
    payload = folder / "payload"
    if payload.is_symlink() or not payload.is_dir():
        raise ValueError("Accepted payload is missing or redirected")
    with ZipFile(archive) as bundle:
        manifest = bundle.read("manifest.json")
        expected = json.loads(manifest)["files"]
        if (payload / "manifest.json").read_bytes() != manifest:
            raise ValueError("Unpacked manifest differs from the signed archive")
        actual = lineage.manifest_for(payload)["files"]
        if any(expected.get(name) != sha for name, sha in actual.items()):
            raise ValueError("Unpacked payload contains changed or unexpected bytes")
        missing = expected.keys() - actual.keys()
        if not missing <= lineage.LEGACY_DATABASE_MEMBERS:
            raise ValueError("Unpacked payload is missing non-database evidence")
        return len(missing), sum(bundle.getinfo(name).file_size for name in missing)


def controls_status(v, trusted, key):
    spec = v.get("control", {})
    if not spec.get("enabled"):
        return {"controls_verified": False, "automatic_enabled": False}
    context = {"profile": HUMAN_PROFILE, "career": trusted["career"],
               "test_only": bool(trusted["test_only"]), "repository_id": v["repository_id"],
               "human_id": spec["human_id"], "human_login": spec["human_login"]}
    gate = HumanGate(spec["human_gate"], key, Path(spec["authenticator_file"]).read_bytes(), context)
    with snapshot(gate.path) as db:
        row = db.execute("SELECT * FROM configuration").fetchone()
        if row["context"] != canonical_json(gate.context) or not hmac.compare_digest(
                row["seal"], lineage.sign(key, gate._state(db))):
            raise ValueError("Human gate binding or journal seal differs")
    who = SimpleNamespace(key=key, career=trusted["career"], test_only=bool(trusted["test_only"]))
    controls = Controls(who, spec["store"], spec["directory"], spec["policy_receipt"], gate,
                        enabled=True, production_binding_approved=spec["production_binding_approved"])
    with snapshot(controls.store) as db:
        if not hmac.compare_digest(db.execute("SELECT signature FROM integrity").fetchone()[0],
                                   lineage.sign(key, controls._document(db))):
            raise ValueError("Control preparation journal seal differs")
    receipt = lineage.check_signed(lineage.read_json(controls.policy_receipt), key)
    expected = {"profile": CONTROL_PROFILE, "action": "approve_remote_control_policies",
                "career": who.career, "test_only": who.test_only, "authority_key_sha256": trusted["key_hash"],
                "policy_sha256": digest(json.loads(trusted["policy_json"])), "repository_id": v["repository_id"],
                "human_id": spec["human_id"], "human_login": spec["human_login"], "operations": OPERATIONS}
    if receipt != expected or (not who.test_only and not controls.production_binding_approved):
        raise ValueError("Missing exact signed control policy binding")
    mode = lineage.check_signed(lineage.read_json(Path(v["automatic_directory"]) / "mode.json"), key)
    if (mode["profile"], mode["career"], mode["test_only"], mode["repository_id"], mode["human_id"]) != (
            "career-automatic-gameplay-1", who.career, who.test_only, v["repository_id"], spec["human_id"]):
        raise ValueError("Automatic delegation belongs to a different authority")
    return {"controls_verified": True, "automatic_enabled": mode["enabled"]}


def inspect(config_path, scratch):
    v = config(config_path)
    key = Path(v["key_file"]).read_bytes()
    with snapshot(v["registry"]) as db:
        trusted = lineage.authority(db, key)
        if trusted["career"] != v["career"] or bool(trusted["test_only"]) is not v["test_only"] or not trusted["active"]:
            raise ValueError("Wrong or fenced local authority")
        lineage.check_cursors(db, trusted, key)
        page_count = 0
        for page in db.execute("SELECT * FROM narration_pages"):
            statement = lineage.page_statement(page["id"], page["checkpoint"], page["request_sha"],
                                               json.loads(page["response"]), trusted)
            if not hmac.compare_digest(page["signature"], lineage.sign(key, statement)):
                raise ValueError("Narration page signature differs")
            page_count += 1
        rows = db.execute("SELECT * FROM accepted ORDER BY generation").fetchall()
        proofs = [json.loads(r["proof"]) for r in rows]
        if not rows or lineage.verify_chain(proofs, trusted, key) != trusted["head"]:
            raise ValueError("Expected a signed legacy successor chain")
        if file_sha256(Path(v["root_parent"])) != lineage.ROOT:
            raise ValueError("Local root bytes differ from the accepted root")
        inventories = [inventory(Path(r["path"]), p) for r, p in zip(rows, proofs, strict=True)]
        head = Path(rows[-1]["path"])
        with tempfile.TemporaryDirectory(dir=scratch, prefix="braga-preflight-") as tmp:
            info, _ = lineage.stage_legacy_parent(db, trusted, key, head, tmp)
            with lineage.calculation(bool(trusted["test_only"])):
                lineage.verify_payload(info["payload"], trusted, key)
            closure = season_authority._closure(info, db, trusted, key)
            with connect_read_only(info["database"]) as world:
                foreign_keys = len(world.execute("PRAGMA foreign_key_check").fetchall())
                missing_country = world.execute("SELECT count(*) FROM world_clubs WHERE country IS NULL").fetchone()[0]
            report = {"checkpoint": info["checkpoint"], "generation": info["generation"], "clock": info["clock"],
                      "signed_archives": len(proofs), "archive_head_replayed": True,
                      "unpacked_head_usable": not inventories[-1][0],
                      "payloads_needing_repair": sum(bool(count) for count, _ in inventories),
                      "missing_database_members": sum(count for count, _ in inventories),
                      "repair_uncompressed_bytes": sum(size for _, size in inventories),
                      "cursor_count": db.execute("SELECT count(*) FROM cursors").fetchone()[0],
                      "signed_pages": page_count,
                      "head_claimed": bool(db.execute("SELECT 1 FROM parent_claims WHERE parent=?", (trusted["head"],)).fetchone()),
                      "foreign_key_violations": foreign_keys, "club_country_gaps": missing_country,
                      "unrevealed_matches": closure["unrevealed_matches"], "closure_blockers": closure["blockers"],
                      "competitions": [{"competition": x["competition"], "completed": x["completed"],
                                        "pending": len(x["pending"]), "missing_scores": x["missing_scores"]}
                                       for x in closure["competitions"]]}
        report.update(controls_status(v, trusted, key))
    with snapshot(v["ledger"]) as db:
        check_ledger(db, key)
        report["next_sequence"] = db.execute("SELECT next_sequence FROM meta").fetchone()[0]
        report["unfinished_requests"] = db.execute("SELECT count(*) FROM requests WHERE response IS NULL").fetchone()[0]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path, help="Existing disposable workspace directory")
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    tempfile.tempdir = str(scratch)
    print(json.dumps(inspect(args.config, scratch), indent=2))
