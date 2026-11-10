"""Local, one-time import of the reviewed episode #81 alternate archive."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import secrets
import shutil
from uuid import uuid4
from zipfile import ZipFile

from braga_era import lineage, season_lineage as seasons, season_objects
from braga_era.bridge.__main__ import config, build
from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN
from braga_era.bridge.automatic import Automatic
from braga_era.bridge.career import Career
from braga_era.bridge.control import Controls, OPERATIONS, PROFILE as CONTROL
from braga_era.db import connect_read_only, file_sha256
from braga_era.engine.substitutions import VERSION
from braga_era.history import digest
from braga_era.multiseason import fork
from braga_era.multiseason.execution import ENGINE_ACTIVATION
from braga_era.seasons import fingerprints

CAREER = "the-braga-era-alt-episode81"
ORIGINAL = "934cd77500e2f2805ce12f6b4ad6c194345fddcd928d410d59b61404df7c2ace"


def verified_source(backup, original_config, output):
    old_key = Path(original_config["key_file"]).read_bytes()
    for filename, checkpoint in (("original-verified.json", ORIGINAL), ("rewind-verified.json", fork.SOURCE)):
        doc = lineage.check_signed(lineage.read_json(backup / filename), old_key)
        if doc["checkpoint"] != checkpoint or doc["independent_restore"] is not True:
            raise ValueError("Wrong independently restored original or rewind source")
    handoff = lineage.check_signed(lineage.read_json(backup / "original/handoff.json"), old_key)
    if handoff["head"] != ORIGINAL or handoff["transfer"] or handoff["files"] != {
        name: file_sha256(backup / "original" / name) for name in handoff["files"]
    }:
        raise ValueError("Original career backup differs")
    detached = backup / "alternate-feb14"
    key = (detached / "fork.key").read_bytes()
    if key == old_key:
        raise ValueError("Detached and original signers must be separate")
    proof = lineage.check_signed(lineage.read_json(detached / "verification.json"), key)
    archive = detached / "alternate-checkpoint.zip"
    if (file_sha256(archive) != fork.ARCHIVE or proof["archive_sha256"] != fork.ARCHIVE
            or proof["checkpoint"] != fork.DETACHED or proof["source_checkpoint"] != fork.SOURCE
            or not all(proof[x] is True for x in ("independent_restore", "independent_replay", "exact_sqlite_replay"))
            or proof["production_eligible"] is not False):
        raise ValueError("Detached verification differs from the authorized archive")
    with ZipFile(archive) as z:
        if set(z.namelist()) != {"world.sqlite", "checkpoint.json", "seed-commitment.json", "claim-receipt.json"}:
            raise ValueError("Unexpected detached archive inventory")
        meta, seed, claim = (lineage.check_signed(json.loads(z.read(name)), key)
                             for name in ("checkpoint.json", "seed-commitment.json", "claim-receipt.json"))
        if (digest(meta) != fork.DETACHED or meta["seed_commitment_sha256"] != digest(seed)
                or meta["claim_sha256"] != digest(claim) or claim["commitment_sha256"] != digest(seed)
                or seed["source_checkpoint"] != fork.SOURCE or seed["fixture"] != meta["fixture"]
                or z.getinfo("world.sqlite").file_size > 2 * 1024**3):
            raise ValueError("Detached manifest or committed seed differs")
        with z.open("world.sqlite") as src, output.open("xb") as out:
            shutil.copyfileobj(src, out)
    if file_sha256(output) != meta["database_sha256"]:
        raise ValueError("Restored detached world differs from the verified bytes")
    rewind = backup / "rewind-restored/world/database.sqlite"
    with ZipFile(backup / "rewind-parent.zip") as z:
        parent = json.loads(z.read("package.json"))
    if digest(parent["metadata"]) != fork.SOURCE or file_sha256(rewind) != parent["metadata"]["database_sha256"]:
        raise ValueError("Rewind source bytes differ")
    with connect_read_only(output) as db, connect_read_only(rewind) as parent_db:
        if digest(fingerprints(db)) != meta["world_sha256"]:
            raise ValueError("Restored detached table fingerprints differ")
        before = dict(parent_db.execute("SELECT fixture,result_sha256 FROM ms_executions"))
        after = dict(db.execute("SELECT fixture,result_sha256 FROM ms_executions"))
        if ({k: after[k] for k in before} != before
                or set(after) - set(before) != set(claim["claim"]["committed_fixtures"])):
            raise ValueError("Historical fixture commitments differ")
        row = db.execute("SELECT * FROM ms_executions WHERE fixture=?", (meta["fixture"],)).fetchone()
        result = json.loads(row["result_json"])
        version = json.loads(row["config_json"])["version"]
        tie = db.execute("""SELECT t.winner FROM ms_ties t JOIN ms_fixtures f ON f.tie_key=t.key
                            WHERE f.key=? AND f.status='final'""", (meta["fixture"],)).fetchone()
        if (digest(result) != row["result_sha256"] or row["result_sha256"] != proof["result_sha256"]
                or version != "braga-headless-1.1.0" or result["score"] != [0, 1]
                or result["resolution"]["aggregate_home_away"] != [2, 4] or tie[0] != "club:15"
                or json.loads(row["seed_json"])["root_sha256"] != claim["root_sha256"]
                or json.loads(row["seed_json"])["requested_seed"] != seed["requested_seed"]):
            raise ValueError("Approved match result, qualifying tie or commitment differs")
    return meta, seed, version, before


def bridge(root, old, registry, key_path, key, test):
    cfg = {**old, "career": CAREER, "test_only": test, "registry": str(registry), "key_file": str(key_path),
           "ledger": str(root / "bridge/ledger.sqlite"), "automatic_directory": str(root / "automatic")}
    local = dict(old["control"])
    # Read the existing authenticator locally. Keep the original files intact.
    local.update(store=str(root / "control/preparations.sqlite"), directory=str(root / "control/executions"),
                 policy_receipt=str(root / "control/policy.json"), human_gate=str(root / "control/gate.sqlite"))
    cfg["control"] = local
    career = Career(registry, key, CAREER, test)
    context = {"profile": HUMAN, "career": CAREER, "test_only": test, "repository_id": old["repository_id"],
               "human_id": local["human_id"], "human_login": local["human_login"]}
    secret = secrets.token_bytes(32) if test else Path(local["authenticator_file"]).read_bytes()
    if test:
        path = root / "test-authenticator.key"
        path.write_bytes(secret)
        local["authenticator_file"] = str(path)
    gate = HumanGate(local["human_gate"], key, secret, context)
    gate.initialize()
    with lineage.access(registry, key) as (_, t):
        policy = {"profile": CONTROL, "action": "approve_remote_control_policies", "career": CAREER,
                  "test_only": test, "authority_key_sha256": t["key_hash"],
                  "policy_sha256": digest(json.loads(t["policy_json"])), "repository_id": old["repository_id"],
                  "human_id": local["human_id"], "human_login": local["human_login"], "operations": OPERATIONS}
    lineage.publish_json(Path(local["policy_receipt"]), lineage.signed(policy, key))
    controls = Controls(career, local["store"], local["directory"], local["policy_receipt"], gate,
                        enabled=True, production_binding_approved=not test)
    controls.initialize()
    Automatic(controls, cfg["automatic_directory"]).initialize()
    lineage.publish_json(root / "config.json", cfg)
    return build(config(root / "config.json"), "")


def run(root, backup, original_config, test):
    old = config(original_config)
    archive_db = root / "restored-alt.sqlite"
    meta, seed, version, _ = verified_source(backup, old, archive_db)
    key = secrets.token_bytes(32)
    key_path = root / "commissioner.key"
    with key_path.open("xb") as out:
        out.write(key)
    registry = root / "authority/career.sqlite"
    lineage.provision(registry, key, test_only=test, commissioner="Lbragaa", career_id=CAREER,
                      seed=seed["requested_seed"])
    policy = seasons.policy(test)
    with lineage.access(registry, key) as (_, t):
        committed_seed = t["seed"]
    origin = {"action": fork.ACTION, "profile": seasons.PROFILE, "test_only": test, "career": CAREER,
              "parent_checkpoint": fork.DETACHED, "source_checkpoint": fork.SOURCE, "archive_sha256": fork.ARCHIVE,
              "parent_sha256": meta["database_sha256"], "policy_sha256": digest(policy),
              "seed_sha256": digest(committed_seed), "replay_seed_commitment_sha256": digest(seed),
              "historical_engine": version, "result_sha256": meta["result_sha256"]}
    marker = {"profile": seasons.PROFILE, "test_only": test, "acceptance_eligible": True,
              "decision": origin, "signature": lineage.sign(key, origin), "seed": committed_seed, "policy": policy}
    staging = root / "world-staging"
    fork.initialize(archive_db, staging, marker, key)
    archive_db.unlink()
    imported = root / "accepted-import"
    request_id = str(uuid4())
    initial = seasons.stage_episode81_import(registry, key, staging, imported, request_id)
    season_objects.remove_owned(staging, root)
    decision = seasons.acceptance_template(registry, key, imported)
    assert seasons.accept_episode81_import(registry, key, imported, lineage.signed(decision, key)) == initial
    print("Exact restored archive registered, preserving the February 14 replay.", flush=True)
    activation = seasons.prepare(registry, key, str(uuid4()),
                                 [{"kind": ENGINE_ACTIVATION, "args": {"engine_version": VERSION}}])
    lineage.publish_json(root / "engine-activation-manifest.json", activation)
    seasons.authorize(registry, key, activation, lineage.signed(seasons.authorization(activation), key))
    successor = root / "accepted-engine"
    candidate = seasons.execute(registry, key, activation["request_id"], successor)
    decision = seasons.acceptance_template(registry, key, successor)
    receipt = seasons.accept(registry, key, successor, decision, lineage.sign(key, decision))
    assert receipt["checkpoint_sha256"] == candidate["checkpoint_sha256"]
    status = fork.status(registry, key)
    assert status["engine_version"] == VERSION
    with lineage.access(registry, key) as (c, t):
        current, _ = seasons.current(c, t, key)
    with connect_read_only(current["world"] / "parent.sqlite") as old_db, connect_read_only(current["database"]) as db:
        assert (old_db.execute("SELECT * FROM ms_executions ORDER BY fixture").fetchall()
                == db.execute("SELECT * FROM ms_executions ORDER BY fixture").fetchall())
        assert old_db.execute("SELECT clock FROM ms_meta").fetchone()[0] == status["clock"]
    if test:
        from .rehearse_episode81_fork import check
        check(root, registry, key, successor, bridge(root, old, registry, key_path, key, test), status)
    else:
        bridge(root, old, registry, key_path, key, test)
    print(json.dumps(status), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--original-config", required=True, type=Path)
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    if not args.root.resolve(strict=True).is_dir() or any(args.root.iterdir()):
        raise ValueError("Use a fresh, secured, empty fork directory")
    if args.root.resolve().is_relative_to(args.original_config.resolve().parent) or args.root.resolve().is_relative_to(args.backup.resolve()):
        raise ValueError("Keep the fork outside the original career and its backup")
    run(args.root.resolve(), args.backup.resolve(), args.original_config.resolve(), not args.production)
