"""Registered immediate-parent continuations over the existing world executor.

Accepted snapshot bytes are immutable. Career seeds never change between batches.
The embedded 046C root is historical evidence, not the execution parent after G1.
"""

from contextlib import closing, contextmanager
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
import time
import zipfile

from .acceptance import catalog
from .checkpoints import (
    write_json,
    read_json,
    manifest_for,
    _publish_file,
    _check_destination,
)
from .db import file_sha256, connect_read_only
from .history import canonical_json as encode, digest
from .forward import sign, planned_fixtures
from .world.policy import ReadinessPolicy
from .world.forward_config import configuration
from .world.scope import calculation
from .world.storage import create, writer, process_lock, authenticate
from .world.runner import advance, pending, InjectedCrash
from .world.packages import fingerprints
from .world.audit import audit
from .world.players import moment

PROFILE = "continuous-forward-lineage-2"
SEED_POLICY = "career-stable-per-fixture-1"
ROOT = catalog()["database_sha256"]
REQUIRED = [
    "rosters",
    "historical_unknowns",
    "engine_configuration",
    "player_timeline",
    "competition_rules_and_draws",
    "financial_restrictions",
    "specified_batch",
]
FILES = {
    "database.sqlite",
    "immediate_parent.sqlite",
    "history_root.sqlite",
    "world.json",
    "initialization_commitment.json",
    "lineage.json",
    "authorization.json",
    "narration.json",
    "checkpoint.json",
    "validation.json",
}
DDL = """
CREATE TABLE authority(profile TEXT PRIMARY KEY,key_hash TEXT NOT NULL,test_only INTEGER NOT NULL,commissioner TEXT NOT NULL,career TEXT NOT NULL,seed TEXT NOT NULL,policy_json TEXT NOT NULL,head TEXT NOT NULL,active INTEGER NOT NULL,lease_epoch INTEGER NOT NULL,transfer_target TEXT,signature TEXT NOT NULL);
CREATE TABLE batches(id TEXT PRIMARY KEY,parent TEXT NOT NULL,manifest TEXT NOT NULL,decision TEXT NOT NULL,signature TEXT NOT NULL,state TEXT NOT NULL,directory TEXT,parent_path TEXT NOT NULL,checkpoint TEXT,package_sha TEXT);
CREATE TABLE parent_claims(parent TEXT PRIMARY KEY,batch TEXT UNIQUE NOT NULL);
CREATE TABLE fixture_claims(fixture TEXT PRIMARY KEY,batch TEXT NOT NULL,seed_policy TEXT NOT NULL);
CREATE TABLE obligation_claims(obligation TEXT PRIMARY KEY,batch TEXT NOT NULL);
CREATE TABLE accepted(checkpoint TEXT PRIMARY KEY,parent TEXT UNIQUE NOT NULL,generation INTEGER UNIQUE NOT NULL,proof TEXT NOT NULL,path TEXT NOT NULL);
CREATE TABLE decisions(id INTEGER PRIMARY KEY,batch TEXT NOT NULL,kind TEXT NOT NULL,document TEXT NOT NULL,signature TEXT NOT NULL);
CREATE TABLE cursors(fixture TEXT PRIMARY KEY,result_sha TEXT NOT NULL,sequence INTEGER NOT NULL);
CREATE TABLE narration_pages(id TEXT PRIMARY KEY,checkpoint TEXT NOT NULL,request_sha TEXT NOT NULL,response TEXT NOT NULL,signature TEXT NOT NULL);
CREATE TABLE cursor_revision(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,signature TEXT NOT NULL);
INSERT INTO cursor_revision VALUES(1,0,'');
"""


@contextmanager
def staged_directory(destination):
    """Recover only our unpublished staging tree after an interrupted process."""
    destination = _check_destination(Path(destination)).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    token = digest(str(destination))[:16]
    with process_lock(destination.parent, name=f".lp-{token}.lock") as lease:
        _check_destination(destination)

        def remove_owned(path):
            path = Path(path)
            if path.parent.resolve() != destination.parent or not path.name.startswith(
                f".lp-{token}-"
            ):
                raise ValueError("Invalid unpublished checkpoint ownership")
            if path.exists():
                attrs = getattr(path.lstat(), "st_file_attributes", 0)
                if path.is_symlink() or attrs & getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
                ):
                    raise ValueError("Redirected unpublished checkpoint")
                shutil.rmtree(path)

        lease.seek(1)
        previous = lease.read()
        if previous:
            record = json.loads(previous)
            if record["profile"] != PROFILE or record["target"] != str(destination):
                raise ValueError("Invalid checkpoint publication journal")
            remove_owned(record["staging"])
        stage = Path(tempfile.mkdtemp(prefix=f".lp-{token}-", dir=destination.parent))
        lease.seek(1)
        lease.truncate()
        lease.write(
            encode(
                {"profile": PROFILE, "target": str(destination), "staging": str(stage)}
            ).encode()
        )
        lease.flush()
        os.fsync(lease.fileno())
        try:
            yield stage
            for attempt in range(4):
                _check_destination(destination)
                try:
                    stage.rename(destination)
                    break
                except PermissionError:
                    if attempt == 3 or destination.exists():
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            remove_owned(stage)
            lease.seek(1)
            lease.truncate()
            lease.flush()
            os.fsync(lease.fileno())


def connect(path):
    if not Path(path).is_file():
        raise ValueError("Missing lineage authority registry")
    c = sqlite3.connect(path, isolation_level=None, timeout=0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA synchronous=FULL")
    return c


def authority(c, key):
    row = c.execute("SELECT * FROM authority").fetchone()
    if (
        not row
        or row["profile"] != PROFILE
        or not hmac.compare_digest(row["key_hash"], hashlib.sha256(key).hexdigest())
    ):
        raise ValueError("Untrusted lineage profile or signing key")
    if json.loads(row["policy_json"]) != asdict(ReadinessPolicy()):
        raise ValueError("Unsupported lineage world policy")
    if not hmac.compare_digest(
        row["signature"],
        sign(key, {k: row[k] for k in row.keys() if k not in ("head", "signature")}),
    ):
        raise ValueError("Authority configuration was tampered")
    latest = c.execute(
        "SELECT checkpoint FROM accepted ORDER BY generation DESC LIMIT 1"
    ).fetchone()
    if row["head"] != (latest[0] if latest else ROOT):
        raise ValueError("Accepted lineage head pointer was tampered")
    return row


def provision(registry, key, *, test_only, commissioner, career_id, seed):
    """Explicit trust bootstrap. Task 03D calls only test_only=True."""
    sign(key, {})
    if type(test_only) is not bool or not commissioner or not career_id or not seed:
        raise ValueError("Explicit authority, career and committed seed required")
    registry = _check_destination(Path(registry))
    registry.parent.mkdir(parents=True, exist_ok=True)
    with registry.open("xb"):
        pass
    with closing(connect(registry)) as c:
        c.executescript(DDL)
        static = {
            "profile": PROFILE,
            "key_hash": hashlib.sha256(key).hexdigest(),
            "test_only": int(test_only),
            "commissioner": commissioner,
            "career": career_id,
            "seed": "lineage-career-v1:" + career_id + ":" + str(seed),
            "policy_json": encode(asdict(ReadinessPolicy())),
            "active": 1,
            "lease_epoch": 0,
            "transfer_target": None,
        }
        c.execute(
            "INSERT INTO authority(profile,key_hash,test_only,commissioner,career,seed,policy_json,active,lease_epoch,transfer_target,head,signature) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (*static.values(), ROOT, sign(key, static)),
        )
        trusted = authority(c, key)
        seal_cursors(c, trusted, key)


def signed(document, key):
    return {"document": document, "signature": sign(key, document)}


def check_signed(item, key):
    if (
        not isinstance(item, dict)
        or set(item) != {"document", "signature"}
        or not hmac.compare_digest(sign(key, item["document"]), item["signature"])
    ):
        raise ValueError("Incorrect or missing commissioner signature")
    return item["document"]


@contextmanager
def access(registry, key, lock=False, *, allow_fenced=False):
    with closing(connect(registry)) as c:
        trusted = authority(c, key)
        if lock and not trusted["active"] and not allow_fenced:
            raise ValueError(
                "This authority was transferred/fenced; use the active restored runtime"
            )
        with calculation(bool(trusted["test_only"])):
            if lock:
                with process_lock(Path(registry).resolve().parent):
                    yield c, trusted
            else:
                yield c, trusted


def identity(trusted):
    return {
        "profile": PROFILE,
        "career": trusted["career"],
        "test_only": bool(trusted["test_only"]),
        "commissioner": trusted["commissioner"],
    }


def expected_authorization(manifest, trusted):
    return {
        **identity(trusted),
        "action": "authorize_lineage_batch",
        "manifest_sha256": digest(manifest),
        "approvals": REQUIRED,
    }


def validate_manifest_model(manifest, trusted):
    if (
        any(manifest.get(k) != v for k, v in identity(trusted).items())
        or manifest.get("seed_policy") != SEED_POLICY
        or manifest.get("career_seed_sha256") != digest(trusted["seed"])
        or manifest.get("policy") != json.loads(trusted["policy_json"])
        or manifest.get("required_approvals") != REQUIRED
        or manifest.get("configurations")
        != {
            "normal": asdict(configuration(ReadinessPolicy())),
            "neutral_final": asdict(configuration(ReadinessPolicy(), True)),
        }
    ):
        raise ValueError("Unsupported or inconsistent authorized model/seed policy")


def expected_acceptance(meta, package_sha, trusted):
    return {
        **identity(trusted),
        "action": "accept_lineage_checkpoint",
        "checkpoint_sha256": digest(meta),
        "immediate_parent_sha256": meta["immediate_parent_sha256"],
        "package_sha256": package_sha,
    }


def verify_chain(nodes, trusted, key):
    previous = ROOT
    for generation, node in enumerate(nodes, 1):
        meta = node["metadata"]
        checkpoint = digest(meta)
        if (
            meta["profile"] != PROFILE
            or meta["career"] != trusted["career"]
            or meta["test_only"] != bool(trusted["test_only"])
            or meta["generation"] != generation
            or meta["immediate_parent_sha256"] != previous
            or meta["root_sha256"] != ROOT
        ):
            raise ValueError("Broken, unrelated or mixed-mode accepted lineage")
        if (
            meta["seed_policy"] != SEED_POLICY
            or meta["career_seed_sha256"] != digest(trusted["seed"])
            or meta["policy_sha256"] != digest(json.loads(trusted["policy_json"]))
        ):
            raise ValueError("Changed inherited seed/model policy")
        auth = check_signed(node["authorization"], key)
        validate_manifest_model(node["manifest"], trusted)
        if (
            auth != expected_authorization(node["manifest"], trusted)
            or digest(node["manifest"]) != meta["manifest_sha256"]
        ):
            raise ValueError("Lineage execution authority differs")
        validation = check_signed(node["validation"], key)
        if validation != {
            **identity(trusted),
            "action": "independent_lineage_validation",
            "checkpoint_sha256": checkpoint,
            "world_sha256": meta["world_sha256"],
            "independent_delta_replay": True,
        }:
            raise ValueError("Missing independent ancestor validation")
        accepted = check_signed(node["acceptance"], key)
        if accepted != expected_acceptance(meta, node["package_sha256"], trusted):
            raise ValueError("Unaccepted parent in lineage")
        previous = checkpoint
    return previous


def parent_info(c, trusted, key, parent, *, require_head=True):
    parent = Path(parent).resolve()
    if parent.is_file():
        if file_sha256(parent) != ROOT:
            raise ValueError("Unrelated root database")
        if require_head and trusted["head"] != ROOT:
            raise ValueError(
                "Stale original root; use the immediate accepted checkpoint"
            )
        return {
            "checkpoint": ROOT,
            "database": parent,
            "history_root": parent,
            "nodes": [],
            "generation": 0,
            "clock": "2027-09-26 23:30",
            "world_sha256": None,
        }
    payload = parent / "payload"
    meta = read_json(payload / "checkpoint.json")
    checkpoint = digest(meta)
    row = c.execute(
        "SELECT * FROM accepted WHERE checkpoint=?", (checkpoint,)
    ).fetchone()
    if not row or require_head and trusted["head"] != checkpoint:
        raise ValueError("Parent is unaccepted, stale or conflicting")
    proof = json.loads(row["proof"])
    nodes = read_json(payload / "lineage.json") + [proof]
    if verify_chain(nodes, trusted, key) != checkpoint or proof["metadata"] != meta:
        raise ValueError("Accepted parent proof mismatch")
    if file_sha256(parent / "checkpoint.zip") != proof["package_sha256"] or read_json(
        payload / "manifest.json"
    ) != manifest_for(payload):
        raise ValueError("Accepted parent package was tampered")
    if (
        meta["supporting_sha256"]
        != {
            name: file_sha256(payload / name)
            for name in sorted(FILES - {"checkpoint.json", "validation.json"})
        }
        or read_json(payload / "validation.json") != proof["validation"]
    ):
        raise ValueError("Accepted supporting provenance changed")
    if (
        file_sha256(payload / "database.sqlite") != meta["database_sha256"]
        or file_sha256(payload / "history_root.sqlite") != ROOT
    ):
        raise ValueError("Immediate accepted parent hash mismatch")
    with connect_read_only(payload / "database.sqlite") as db:
        if digest(fingerprints(db)) != meta["world_sha256"] or pending(db):
            raise ValueError("Accepted parent state differs from validated receipt")
    return {
        "checkpoint": checkpoint,
        "database": payload / "database.sqlite",
        "history_root": payload / "history_root.sqlite",
        "payload": payload,
        "nodes": nodes,
        "generation": meta["generation"],
        "clock": meta["clock"],
        "world_sha256": meta["world_sha256"],
    }


def inventory(info, until):
    boundary = moment(until)
    if (boundary.hour, boundary.minute, boundary.second, boundary.microsecond) != (
        23,
        59,
        0,
        0,
    ):
        raise ValueError(
            "Profile 2 requires a reviewed complete end-of-day boundary at 23:59"
        )
    if boundary <= moment(info["clock"]) or boundary > moment("2027-12-31 23:59:59"):
        raise ValueError("Unsupported or non-forward chronological boundary")
    if info["generation"] == 0:
        import calendar

        return planned_fixtures(info["database"], until), [
            f"payroll:2027-{m:02}"
            for m in range(9, 13)
            if moment(f"2027-{m:02}-{calendar.monthrange(2027,m)[1]} 23:59") <= boundary
        ]
    fixtures = set()
    with connect_read_only(info["database"]) as db:
        for f in db.execute(
            "SELECT * FROM world_fixtures WHERE status<>'final' AND kickoff<=? ORDER BY key",
            (until,),
        ):
            if ":reserve:" not in f["key"]:
                fixtures.add(f["key"])
                continue
            if db.execute(
                "SELECT 1 FROM world_draws WHERE key=? AND status='activated'",
                (f"{f['competition']}:{f['stage']}",),
            ).fetchone():
                continue
            size = {"R16": 8, "QF": 4, "SF": 2, "FINAL": 1}[f["stage"]]
            fixtures.update(
                f"{f['competition'].lower()}:{f['stage']}-{i:02}:L{f['leg']}"
                for i in range(1, size + 1)
            )
        obligations = [
            r[0]
            for r in db.execute(
                "SELECT key FROM world_obligations WHERE status='scheduled' AND kickoff<=? ORDER BY key",
                (until,),
            )
        ]
    return sorted(fixtures), obligations


def prepare(registry, key, parent, *, until, execution_id):
    with access(registry, key) as (c, trusted):
        info = parent_info(c, trusted, key, parent)
        fixtures, obligations = inventory(info, until)
        if not execution_id or not (fixtures or obligations):
            raise ValueError("Explicit nonempty chronological batch required")
        return {
            **identity(trusted),
            "execution_id": execution_id,
            "immediate_parent_sha256": info["checkpoint"],
            "immediate_parent_database_sha256": file_sha256(info["database"]),
            "generation": info["generation"] + 1,
            "until": until,
            "fixtures": fixtures,
            "obligations": obligations,
            "seed_policy": SEED_POLICY,
            "career_seed_sha256": digest(trusted["seed"]),
            "policy": json.loads(trusted["policy_json"]),
            "configurations": {
                "normal": asdict(configuration(ReadinessPolicy())),
                "neutral_final": asdict(configuration(ReadinessPolicy(), True)),
            },
            "required_approvals": REQUIRED,
        }


def authorize(registry, key, parent, manifest, decision, signature):
    with access(registry, key, True) as (c, trusted):
        expected = prepare(
            registry,
            key,
            parent,
            until=manifest["until"],
            execution_id=manifest["execution_id"],
        )
        if (
            manifest != expected
            or decision != expected_authorization(manifest, trusted)
            or not hmac.compare_digest(sign(key, decision), signature)
        ):
            raise ValueError("Wrong, incomplete or unsigned lineage authorization")
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute(
                "INSERT INTO parent_claims VALUES(?,?)",
                (manifest["immediate_parent_sha256"], manifest["execution_id"]),
            )
            c.executemany(
                "INSERT INTO fixture_claims VALUES(?,?,?)",
                [
                    (f, manifest["execution_id"], SEED_POLICY)
                    for f in manifest["fixtures"]
                ],
            )
            c.executemany(
                "INSERT INTO obligation_claims VALUES(?,?)",
                [(o, manifest["execution_id"]) for o in manifest["obligations"]],
            )
            c.execute(
                "INSERT INTO batches VALUES(?,?,?,?,?,'authorized',NULL,?,NULL,NULL)",
                (
                    manifest["execution_id"],
                    manifest["immediate_parent_sha256"],
                    encode(manifest),
                    encode(decision),
                    signature,
                    str(Path(parent).resolve()),
                ),
            )
            c.execute(
                "INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)",
                (manifest["execution_id"], "execution", encode(decision), signature),
            )
            c.commit()
        except BaseException:
            c.rollback()
            raise


def clone_parent(info, target, career_seed):
    if info["generation"] == 0:
        with staged_directory(Path(target)) as stage:
            bootstrap = stage / "bootstrap"
            create(info["database"], bootstrap, career_seed, ReadinessPolicy())
            for name in (
                "database.sqlite",
                "parent.sqlite",
                "world.json",
                "initialization_commitment.json",
            ):
                (bootstrap / name).rename(stage / name)
            bootstrap.rmdir()
        return
    with staged_directory(Path(target)) as stage:
        shutil.copyfile(info["database"], stage / "database.sqlite")
        shutil.copyfile(info["history_root"], stage / "parent.sqlite")
        for name in ("world.json", "initialization_commitment.json"):
            shutil.copyfile(info["payload"] / name, stage / name)
    authenticate(target)


def prefix_check(parent_db, child_db):
    from .migrations import rows_by_key

    with connect_read_only(parent_db) as old, connect_read_only(child_db) as new:
        has_world = old.execute(
            "SELECT 1 FROM sqlite_master WHERE name='world_receipts'"
        ).fetchone()
        if not has_world:
            return
        for table in (
            "world_executions",
            "world_receipts",
            "world_events",
            "world_performances",
            "world_operations",
            "world_players",
            "world_clubs",
        ):
            a = rows_by_key(old, table)
            b = rows_by_key(new, table)
            if any(b.get(k) != v for k, v in a.items()):
                raise ValueError("Inherited history/commitment changed: " + table)
        for table in ("fixtures", "cdb_2027_legs"):
            a = rows_by_key(old, table)
            b = rows_by_key(new, table)
            if any(
                b.get(k) != v
                for k, v in a.items()
                if table == "cdb_2027_legs" or v["status"] == "final"
            ):
                raise ValueError("Previously completed native result changed")
        for row in old.execute("SELECT * FROM world_draws WHERE status='activated'"):
            if tuple(
                new.execute(
                    "SELECT * FROM world_draws WHERE key=?", (row["key"],)
                ).fetchone()
                or ()
            ) != tuple(row):
                raise ValueError("A committed draw was changed")


def apply_cursors(c, world):
    with writer(world) as (db, p):
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("DELETE FROM world_cursors")
            for row in c.execute("SELECT * FROM cursors ORDER BY fixture"):
                r = db.execute(
                    "SELECT result_sha256,result_json FROM world_executions WHERE fixture_key=?",
                    (row["fixture"],),
                ).fetchone()
                if (
                    not r
                    or r[0] != row["result_sha"]
                    or not 0 <= row["sequence"] <= len(json.loads(r[1])["events"])
                ):
                    raise ValueError("Invalid authoritative narration cursor")
                db.execute("INSERT INTO world_cursors VALUES(?,?,?)", tuple(row))
            db.commit()
        except BaseException:
            db.rollback()
            raise


def zip_payload(payload, archive):
    archive = Path(archive)
    with tempfile.NamedTemporaryFile(dir=archive.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(
            temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9
        ) as z:
            for p in sorted(Path(payload).iterdir()):
                info = zipfile.ZipInfo(p.name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes(), compresslevel=9)
        with temporary.open("r+b") as f:
            f.flush()
            os.fsync(f.fileno())
        _publish_file(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)


def cursor_document(c, trusted):
    return {
        **identity(trusted),
        "action": "narration_progress",
        "source_checkpoint": trusted["head"],
        "revision": c.execute("SELECT revision FROM cursor_revision").fetchone()[0],
        "cursors": [
            dict(r) for r in c.execute("SELECT * FROM cursors ORDER BY fixture")
        ],
    }


def cursor_state(c, trusted):
    doc = cursor_document(c, trusted)
    doc.pop("source_checkpoint")
    doc["action"] = "durable_narration_state"
    return doc


def seal_cursors(c, trusted, key):
    c.execute(
        "UPDATE cursor_revision SET signature=?", (sign(key, cursor_state(c, trusted)),)
    )


def check_cursors(c, trusted, key):
    row = c.execute("SELECT * FROM cursor_revision").fetchone()
    if not row or not hmac.compare_digest(
        row["signature"], sign(key, cursor_state(c, trusted))
    ):
        raise ValueError("Authoritative narration progress was tampered")


def verify_payload(payload, trusted, key, *, replay=True, require_validation=True):
    payload = Path(payload)
    manifest = read_json(payload / "manifest.json")
    if manifest != manifest_for(payload) or set(manifest["files"]) != FILES:
        raise ValueError("Lineage package manifest/inventory mismatch")
    meta = read_json(payload / "checkpoint.json")
    if (
        meta["profile"] != PROFILE
        or meta["format_version"] != 2
        or meta["career"] != trusted["career"]
        or meta["test_only"] != bool(trusted["test_only"])
    ):
        raise ValueError("Unsupported, unrelated or mixed-mode checkpoint")
    nodes = read_json(payload / "lineage.json")
    parent = verify_chain(nodes, trusted, key)
    if (
        meta["immediate_parent_sha256"] != parent
        or meta["generation"] != len(nodes) + 1
    ):
        raise ValueError("Broken immediate-parent lineage")
    root = file_sha256(payload / "history_root.sqlite")
    parent_db = file_sha256(payload / "immediate_parent.sqlite")
    if root != ROOT or parent_db != (
        nodes[-1]["metadata"]["database_sha256"] if nodes else ROOT
    ):
        raise ValueError("Immediate parent or historical root hash mismatch")
    expected_support = {
        p: file_sha256(payload / p)
        for p in sorted(FILES - {"checkpoint.json", "validation.json"})
    }
    if (
        meta["supporting_sha256"] != expected_support
        or meta["database_sha256"] != file_sha256(payload / "database.sqlite")
        or meta["immediate_parent_database_sha256"] != parent_db
    ):
        raise ValueError("Checkpoint supporting bytes changed")
    auth = read_json(payload / "authorization.json")
    execution = auth["manifest"]
    validate_manifest_model(execution, trusted)
    if (
        meta["engine_version"] != configuration(ReadinessPolicy()).version
        or meta["root_sha256"] != ROOT
    ):
        raise ValueError("Unsupported checkpoint engine/root profile")
    if (
        check_signed(
            {"document": auth["decision"], "signature": auth["signature"]}, key
        )
        != expected_authorization(execution, trusted)
        or digest(execution) != meta["manifest_sha256"]
    ):
        raise ValueError("Checkpoint execution authorization mismatch")
    if (
        execution["policy"] != json.loads(trusted["policy_json"])
        or execution["seed_policy"] != SEED_POLICY
        or execution["career_seed_sha256"] != digest(trusted["seed"])
    ):
        raise ValueError("Unapproved policy or replacement career seed")
    info = {
        "checkpoint": parent,
        "database": payload / "immediate_parent.sqlite",
        "history_root": payload / "history_root.sqlite",
        "payload": payload,
        "nodes": nodes,
        "generation": len(nodes),
        "clock": nodes[-1]["metadata"]["clock"] if nodes else "2027-09-26 23:30",
    }
    expected_fixtures, expected_obligations = inventory(info, execution["until"])
    if (
        execution["fixtures"] != expected_fixtures
        or execution["obligations"] != expected_obligations
        or execution["immediate_parent_sha256"] != parent
    ):
        raise ValueError("Unauthorized chronological delta inventory")
    if (
        meta["seed_policy"] != SEED_POLICY
        or meta["career_seed_sha256"] != digest(trusted["seed"])
        or meta["policy_sha256"] != digest(execution["policy"])
    ):
        raise ValueError("Metadata policy identity mismatch")
    prefix_check(payload / "immediate_parent.sqlite", payload / "database.sqlite")
    with connect_read_only(payload / "database.sqlite") as db:
        report = audit(db, payload / "history_root.sqlite")
        if pending(db):
            raise ValueError("Incomplete committed batch cannot be a checkpoint")
        state = dict(db.execute("SELECT * FROM world_info").fetchone())
        if (
            state["seed"] != trusted["seed"]
            or json.loads(state["policy_json"]) != execution["policy"]
            or state["clock"] != meta["clock"]
        ):
            raise ValueError("Checkpoint world identity/clock mismatch")
        expected = fingerprints(db)
        if digest(expected) != meta["world_sha256"]:
            raise ValueError("Checkpoint semantic fingerprint mismatch")
        receipts = {r[0] for r in db.execute("SELECT fixture_key FROM world_receipts")}
        paid = {
            r[0]
            for r in db.execute("SELECT key FROM world_obligations WHERE status='paid'")
        }
        tail = db.execute(
            "SELECT sha256 FROM world_operations ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
        if tail != meta["operation_tail_sha256"]:
            raise ValueError("Operation provenance chain differs")
        narration = check_signed(read_json(payload / "narration.json"), key)
        if (
            narration["action"] != "narration_progress"
            or narration["career"] != trusted["career"]
            or narration["test_only"] != bool(trusted["test_only"])
            or narration["source_checkpoint"] != parent
        ):
            raise ValueError("Invalid approved narration snapshot")
        cursors = [
            dict(
                fixture=r["fixture_key"],
                result_sha=r["result_sha256"],
                sequence=r["sequence"],
            )
            for r in db.execute("SELECT * FROM world_cursors ORDER BY fixture_key")
        ]
        if cursors != narration["cursors"]:
            raise ValueError("Portable narration cursor mismatch")
        for row in cursors:
            result = db.execute(
                "SELECT result_sha256,result_json FROM world_executions WHERE fixture_key=?",
                (row["fixture"],),
            ).fetchone()
            if (
                not result
                or result[0] != row["result_sha"]
                or not 0 <= row["sequence"] <= len(json.loads(result[1])["events"])
            ):
                raise ValueError("Corrupt narration continuation")
    inherited = set()
    old_paid = set()
    if nodes:
        with connect_read_only(payload / "immediate_parent.sqlite") as old:
            inherited = {
                r[0] for r in old.execute("SELECT fixture_key FROM world_receipts")
            }
            old_paid = {
                r[0]
                for r in old.execute(
                    "SELECT key FROM world_obligations WHERE status='paid'"
                )
            }
    if receipts - inherited != set(execution["fixtures"]) or paid - old_paid != set(
        execution["obligations"]
    ):
        raise ValueError("Unexpected or missing executed delta")
    if require_validation:
        check = check_signed(read_json(payload / "validation.json"), key)
        if check != {
            **identity(trusted),
            "action": "independent_lineage_validation",
            "checkpoint_sha256": digest(meta),
            "world_sha256": meta["world_sha256"],
            "independent_delta_replay": True,
        }:
            raise ValueError("Missing signed independent validation")
    if replay:
        with tempfile.TemporaryDirectory(
            dir=payload.parent, prefix=".lineage-delta-"
        ) as temporary:
            scratch = Path(temporary) / "world"
            clone_parent(info, scratch, trusted["seed"])
            advance(scratch, until=execution["until"])
            with connect_read_only(scratch / "database.sqlite") as db:
                if fingerprints(db) != expected:
                    raise ValueError(
                        "Independent immediate-parent delta replay differs"
                    )
    return {
        "ok": True,
        "profile": PROFILE,
        "checkpoint_sha256": digest(meta),
        "generation": meta["generation"],
        "test_only": meta["test_only"],
        "immediate_parent_sha256": parent,
        "independent_delta_replay": replay,
        "receipts": len(receipts),
        "new_receipts": len(receipts - inherited),
        "world_sha256": meta["world_sha256"],
        "validation": report,
    }


def build_payload(c, trusted, key, info, manifest, decision, signature, directory):
    directory = Path(directory)
    payload = directory / "payload"
    world = directory / "world"
    if payload.exists():
        result = verify_payload(payload, trusted, key)
        if read_json(payload / "authorization.json")["manifest"] != manifest:
            raise ValueError("Existing candidate belongs to a different batch")
        return result
    with staged_directory(payload) as stage:
        with writer(world) as (db, p):
            audit(db, world / "parent.sqlite")
            if pending(db):
                raise ValueError("Resume pending execution before publishing")
            shutil.copyfile(world / "database.sqlite", stage / "database.sqlite")
            shutil.copyfile(info["database"], stage / "immediate_parent.sqlite")
            shutil.copyfile(world / "parent.sqlite", stage / "history_root.sqlite")
            for name in ("world.json", "initialization_commitment.json"):
                shutil.copyfile(world / name, stage / name)
            write_json(stage / "lineage.json", info["nodes"])
            write_json(
                stage / "authorization.json",
                {"manifest": manifest, "decision": decision, "signature": signature},
            )
            write_json(
                stage / "narration.json", signed(cursor_document(c, trusted), key)
            )
            meta = {
                "profile": PROFILE,
                "format_version": 2,
                "scope": (
                    "TEST-ONLY NONCANONICAL CONTINUOUS CHECKPOINT"
                    if trusted["test_only"]
                    else "UNACCEPTED FORWARD CHECKPOINT"
                ),
                "test_only": bool(trusted["test_only"]),
                "career": trusted["career"],
                "generation": info["generation"] + 1,
                "root_sha256": ROOT,
                "immediate_parent_sha256": info["checkpoint"],
                "immediate_parent_database_sha256": file_sha256(info["database"]),
                "database_sha256": file_sha256(stage / "database.sqlite"),
                "world_sha256": digest(fingerprints(db)),
                "clock": db.execute("SELECT clock FROM world_info").fetchone()[0],
                "manifest_sha256": digest(manifest),
                "seed_policy": SEED_POLICY,
                "career_seed_sha256": digest(trusted["seed"]),
                "policy_sha256": digest(json.loads(trusted["policy_json"])),
                "engine_version": configuration(ReadinessPolicy()).version,
                "operation_tail_sha256": db.execute(
                    "SELECT sha256 FROM world_operations ORDER BY sequence DESC LIMIT 1"
                ).fetchone()[0],
                "supporting_sha256": {
                    name: file_sha256(stage / name)
                    for name in sorted(FILES - {"checkpoint.json", "validation.json"})
                },
            }
        write_json(stage / "checkpoint.json", meta)
        write_json(stage / "validation.json", {"pending": True})
        write_json(stage / "manifest.json", manifest_for(stage))
        verify_payload(stage, trusted, key, require_validation=False)
        write_json(
            stage / "validation.json",
            signed(
                {
                    **identity(trusted),
                    "action": "independent_lineage_validation",
                    "checkpoint_sha256": digest(meta),
                    "world_sha256": meta["world_sha256"],
                    "independent_delta_replay": True,
                },
                key,
            ),
        )
        write_json(stage / "manifest.json", manifest_for(stage))
    return verify_payload(payload, trusted, key, replay=False)


def execute(registry, key, execution_id, directory, *, crash=None):
    directory = Path(directory).resolve()
    with access(registry, key, True) as (c, trusted):
        check_cursors(c, trusted, key)
        row = c.execute("SELECT * FROM batches WHERE id=?", (execution_id,)).fetchone()
        if not row or row["state"] not in ("authorized", "executing", "candidate"):
            raise ValueError("Batch is not execution-authorized or is already accepted")
        manifest = json.loads(row["manifest"])
        if json.loads(row["decision"]) != expected_authorization(
            manifest, trusted
        ) or not hmac.compare_digest(
            row["signature"], sign(key, json.loads(row["decision"]))
        ):
            raise ValueError("Execution signature changed")
        claims = [
            r[0]
            for r in c.execute(
                "SELECT fixture FROM fixture_claims WHERE batch=? ORDER BY fixture",
                (execution_id,),
            )
        ]
        if (
            claims != manifest["fixtures"]
            or c.execute(
                "SELECT batch FROM parent_claims WHERE parent=?",
                (manifest["immediate_parent_sha256"],),
            ).fetchone()[0]
            != execution_id
        ):
            raise ValueError("Execution claims differ from the signed batch")
        info = parent_info(c, trusted, key, row["parent_path"])
        if info["checkpoint"] != manifest["immediate_parent_sha256"]:
            raise ValueError("Stale/conflicting execution parent")
        if row["directory"] and Path(row["directory"]) != directory:
            raise ValueError("Resume the original committed execution directory")
        if row["state"] == "candidate":
            return verify_payload(directory / "payload", trusted, key)
        c.execute(
            "UPDATE batches SET state='executing',directory=? WHERE id=?",
            (str(directory), execution_id),
        )
        world = directory / "world"
        if not world.exists():
            directory.mkdir(parents=True, exist_ok=True)
            clone_parent(info, world, trusted["seed"])
            apply_cursors(c, world)
        if crash == "after_parent_copy":
            raise InjectedCrash(crash)
        with connect_read_only(world / "database.sqlite") as db:
            if (
                db.execute("SELECT seed FROM world_info").fetchone()[0]
                != trusted["seed"]
            ):
                raise ValueError("A resumed career cannot allocate a replacement seed")
        advance(world, until=manifest["until"], crash=crash)
        if crash == "after_new_batch":
            raise InjectedCrash(crash)
        result = build_payload(
            c,
            trusted,
            key,
            info,
            manifest,
            json.loads(row["decision"]),
            row["signature"],
            directory,
        )
        if crash == "after_candidate_payload":
            raise InjectedCrash(crash)
        archive = directory / "checkpoint.zip"
        if not archive.exists():
            zip_payload(directory / "payload", archive)
        if crash == "after_archive":
            raise InjectedCrash(crash)
        # Re-open exported bytes independently before a candidate is registered.
        with tempfile.TemporaryDirectory(
            dir=directory, prefix=".verify-zip-"
        ) as temporary:
            restored = Path(temporary) / "payload"
            extract(archive, restored)
            verify_payload(restored, trusted, key)
        c.execute(
            "UPDATE batches SET state='candidate',checkpoint=?,package_sha=? WHERE id=?",
            (result["checkpoint_sha256"], file_sha256(archive), execution_id),
        )
        return {
            **result,
            "package_sha256": file_sha256(archive),
            "acceptance_required": True,
        }


def extract(archive, destination):
    """Format 2 bounds apply only to this registered format; V1 stays 100 MB."""
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if (
            len(infos) != len(FILES) + 1
            or sum(i.file_size for i in infos) > 256_000_000
        ):
            raise ValueError("Lineage archive exceeds registered format-2 bounds")
        names = [i.filename for i in infos]
        if (
            set(names) != FILES | {"manifest.json"}
            or len(set(n.casefold() for n in names)) != len(names)
            or any(
                i.is_dir() or i.external_attr >> 16 & 0o170000 == 0o120000
                for i in infos
            )
        ):
            raise ValueError("Unsafe, duplicate or unexpected lineage archive entry")
        with staged_directory(Path(destination)) as stage:
            for info in infos:
                (stage / info.filename).write_bytes(z.read(info))


def acceptance_template(registry, key, directory):
    with access(registry, key) as (c, trusted):
        directory = Path(directory)
        meta = read_json(directory / "payload/checkpoint.json")
        return expected_acceptance(
            meta, file_sha256(directory / "checkpoint.zip"), trusted
        )


def accept(registry, key, directory, decision, signature, *, crash=None):
    directory = Path(directory).resolve()
    with access(registry, key, True) as (c, trusted):
        meta = read_json(directory / "payload/checkpoint.json")
        auth = read_json(directory / "payload/authorization.json")
        sha = file_sha256(directory / "checkpoint.zip")
        if decision != expected_acceptance(
            meta, sha, trusted
        ) or not hmac.compare_digest(sign(key, decision), signature):
            raise ValueError("Separate exact-hash successor acceptance required")
        row = c.execute(
            "SELECT * FROM batches WHERE id=?", (auth["manifest"]["execution_id"],)
        ).fetchone()
        if (
            not row
            or row["state"] != "candidate"
            or row["checkpoint"] != digest(meta)
            or row["package_sha"] != sha
            or trusted["head"] != meta["immediate_parent_sha256"]
        ):
            raise ValueError("Unaccepted, stale, repeated or conflicting candidate")
        verified = verify_payload(directory / "payload", trusted, key)
        proof = {
            "metadata": meta,
            "manifest": auth["manifest"],
            "authorization": {
                "document": auth["decision"],
                "signature": auth["signature"],
            },
            "validation": read_json(directory / "payload/validation.json"),
            "package_sha256": sha,
            "acceptance": {"document": decision, "signature": signature},
        }
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute(
                "INSERT INTO accepted VALUES(?,?,?,?,?)",
                (
                    verified["checkpoint_sha256"],
                    meta["immediate_parent_sha256"],
                    meta["generation"],
                    encode(proof),
                    str(directory),
                ),
            )
            if (
                c.execute(
                    "UPDATE authority SET head=? WHERE head=?",
                    (verified["checkpoint_sha256"], meta["immediate_parent_sha256"]),
                ).rowcount
                != 1
            ):
                raise ValueError("Accepted head changed concurrently")
            c.execute(
                "UPDATE batches SET state='accepted' WHERE id=?",
                (auth["manifest"]["execution_id"],),
            )
            c.execute(
                "INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)",
                (
                    auth["manifest"]["execution_id"],
                    "acceptance",
                    encode(decision),
                    signature,
                ),
            )
            if crash == "before_accept_commit":
                raise InjectedCrash(crash)
            c.commit()
        except BaseException:
            c.rollback()
            raise
        if crash == "after_accept_commit":
            raise InjectedCrash(crash)
        publish_json(directory / "acceptance.json", proof["acceptance"])
        return {**verified, "accepted": True, "test_only": bool(trusted["test_only"])}


def publish_json(path, document):
    path = Path(path)
    if path.exists():
        if read_json(path) != document:
            raise ValueError("Existing signed receipt differs")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
    try:
        write_json(temporary, document)
        with temporary.open("r+b") as f:
            f.flush()
            os.fsync(f.fileno())
        _publish_file(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def recover_acceptance(registry, key, directory):
    with access(registry, key, True) as (c, trusted):
        directory = Path(directory)
        meta = read_json(directory / "payload/checkpoint.json")
        row = c.execute(
            "SELECT * FROM accepted WHERE checkpoint=?", (digest(meta),)
        ).fetchone()
        if not row:
            raise ValueError("Checkpoint has not been accepted")
        proof = json.loads(row["proof"])
        if proof["metadata"] != meta or proof["package_sha256"] != file_sha256(
            directory / "checkpoint.zip"
        ):
            raise ValueError("Accepted package differs")
        if check_signed(proof["acceptance"], key) != expected_acceptance(
            meta, proof["package_sha256"], trusted
        ):
            raise ValueError("Invalid recorded acceptance")
        publish_json(directory / "acceptance.json", proof["acceptance"])
        return {
            "ok": True,
            "checkpoint_sha256": digest(meta),
            "acceptance_restored": True,
            "test_only": bool(trusted["test_only"]),
        }


def inspect(registry, key):
    from .world.runner import agenda

    with access(registry, key) as (c, trusted):
        result = {
            **identity(trusted),
            "accepted_checkpoint": trusted["head"],
            "seed_policy": SEED_POLICY,
            "production_execution_authorized": False,
            "authority_active": bool(trusted["active"]),
            "lease_epoch": trusted["lease_epoch"],
        }
        if trusted["head"] == ROOT:
            return {
                **result,
                "generation": 0,
                "accepted_clock": "2027-09-26 23:30",
                "next_due_boundary": "2027-09-30 16:00",
                "next_due_matches": 16,
            }
        row = c.execute(
            "SELECT * FROM accepted WHERE checkpoint=?", (trusted["head"],)
        ).fetchone()
        info = parent_info(c, trusted, key, row["path"])
        with connect_read_only(info["database"]) as db:
            due = agenda(db)
            result.update(
                generation=info["generation"],
                accepted_clock=info["clock"],
                next_due=(
                    [
                        {k: r[k] for k in ("key", "kickoff", "kind")}
                        for r in due
                        if r["kickoff"] == due[0]["kickoff"]
                    ]
                    if due
                    else []
                ),
            )
        return result


def gameplay(registry, key, command, fixture=None, count=1, *, page_id=None):
    """Immutable checkpoints plus authoritative cursor sidecar; no result rerolls."""
    from .gameplay import handoff

    with access(registry, key, True) as (c, trusted):
        check_cursors(c, trusted, key)
        if trusted["head"] == ROOT:
            raise ValueError(
                "No accepted forward result yet; inspect/prepare the initial batch"
            )
        if command == "narrate" and not page_id:
            raise ValueError(
                "Narration needs a stable page request ID for crash/delivery retries"
            )
        if page_id:
            cached = c.execute(
                "SELECT * FROM narration_pages WHERE id=?", (page_id,)
            ).fetchone()
            if cached:
                if cached["request_sha"] != digest(
                    {"command": command, "fixture": fixture, "count": count}
                ):
                    raise ValueError(
                        "Narration page ID was reused for a different request"
                    )
                if not hmac.compare_digest(
                    cached["signature"],
                    sign(
                        key,
                        page_statement(
                            cached["id"],
                            cached["checkpoint"],
                            cached["request_sha"],
                            json.loads(cached["response"]),
                            trusted,
                        ),
                    ),
                ):
                    raise ValueError("Stored narration delivery was tampered")
                return json.loads(cached["response"])
        accepted = c.execute(
            "SELECT * FROM accepted WHERE checkpoint=?", (trusted["head"],)
        ).fetchone()
        info = parent_info(c, trusted, key, accepted["path"])
        session = (
            Path(registry).resolve().parent
            / "sessions"
            / f"{info['generation']:04d}-{trusted['head'][:16]}"
        )
        if not session.exists():
            session.parent.mkdir(parents=True, exist_ok=True)
            clone_parent(info, session, trusted["seed"])
        with connect_read_only(session / "database.sqlite") as db:
            if digest(fingerprints(db)) != info["world_sha256"]:
                raise ValueError(
                    "Narration working world differs from accepted immutable state"
                )
        apply_cursors(c, session)
        c.execute("BEGIN IMMEDIATE")
        try:
            result = handoff(session, command, fixture, count)
            result.update(
                profile=PROFILE,
                career=trusted["career"],
                test_only=bool(trusted["test_only"]),
                accepted_checkpoint=trusted["head"],
                accepted=True,
                scope=(
                    "TEST-ONLY NONCANONICAL NARRATION"
                    if trusted["test_only"]
                    else "ACCEPTED FORWARD NARRATION"
                ),
            )
            if command == "narrate":
                with connect_read_only(session / "database.sqlite") as db:
                    cursor = db.execute(
                        "SELECT * FROM world_cursors WHERE fixture_key=?", (fixture,)
                    ).fetchone()
                c.execute("INSERT OR REPLACE INTO cursors VALUES(?,?,?)", tuple(cursor))
                c.execute("UPDATE cursor_revision SET revision=revision+1")
                seal_cursors(c, trusted, key)
                request_sha = digest(
                    {"command": command, "fixture": fixture, "count": count}
                )
                c.execute(
                    "INSERT INTO narration_pages VALUES(?,?,?,?,?)",
                    (
                        page_id,
                        trusted["head"],
                        request_sha,
                        encode(result),
                        sign(
                            key,
                            page_statement(
                                page_id, trusted["head"], request_sha, result, trusted
                            ),
                        ),
                    ),
                )
            c.commit()
            return result
        except BaseException:
            c.rollback()
            raise


def export_cursor(registry, key):
    with access(registry, key) as (c, trusted):
        check_cursors(c, trusted, key)
        return signed(cursor_document(c, trusted), key)


def page_statement(page_id, checkpoint, request_sha, response, trusted):
    return {
        **identity(trusted),
        "action": "narration_delivery",
        "page_id": page_id,
        "checkpoint": checkpoint,
        "request_sha": request_sha,
        "response_sha256": digest(response),
    }


def import_cursor(registry, key, envelope):
    with access(registry, key, True) as (c, trusted):
        check_cursors(c, trusted, key)
        doc = check_signed(envelope, key)
        if (
            {k: doc[k] for k in identity(trusted)} != identity(trusted)
            or doc["action"] != "narration_progress"
            or doc["source_checkpoint"] != trusted["head"]
        ):
            raise ValueError("Unrelated or mixed-mode narration handoff")
        revision = c.execute("SELECT revision FROM cursor_revision").fetchone()[0]
        if doc["revision"] < revision:
            raise ValueError("Stale narration cursor cannot rewind progress")
        if len(doc["cursors"]) != len({r["fixture"] for r in doc["cursors"]}):
            raise ValueError("Duplicate narration cursor identities")
        if (
            doc["revision"] == revision
            and doc["cursors"] != cursor_document(c, trusted)["cursors"]
        ):
            raise ValueError("Conflicting narration revision")
        row = c.execute(
            "SELECT path FROM accepted WHERE checkpoint=?", (trusted["head"],)
        ).fetchone()
        if not row:
            raise ValueError("Cursor must refer to an accepted checkpoint")
        with connect_read_only(Path(row[0]) / "payload/database.sqlite") as db:
            for cursor in doc["cursors"]:
                result = db.execute(
                    "SELECT result_sha256,result_json FROM world_executions WHERE fixture_key=?",
                    (cursor["fixture"],),
                ).fetchone()
                old = c.execute(
                    "SELECT * FROM cursors WHERE fixture=?", (cursor["fixture"],)
                ).fetchone()
                if (
                    not result
                    or cursor["result_sha"] != result[0]
                    or not 0
                    <= cursor["sequence"]
                    <= len(json.loads(result[1])["events"])
                    or old
                    and cursor["sequence"] < old["sequence"]
                ):
                    raise ValueError("Invalid, changed or regressing narration cursor")
        current = {r["fixture"] for r in c.execute("SELECT * FROM cursors")}
        if current - {r["fixture"] for r in doc["cursors"]}:
            raise ValueError("Narration handoff drops completed progress")
        c.execute("BEGIN IMMEDIATE")
        try:
            for row in doc["cursors"]:
                c.execute(
                    "INSERT OR REPLACE INTO cursors VALUES(?,?,?)",
                    (row["fixture"], row["result_sha"], row["sequence"]),
                )
            c.execute("UPDATE cursor_revision SET revision=?", (doc["revision"],))
            seal_cursors(c, trusted, key)
            c.commit()
        except BaseException:
            c.rollback()
            raise
        return {
            "ok": True,
            "revision": doc["revision"],
            "fixture_cursors": len(doc["cursors"]),
        }


def restore(registry, key, archive, destination):
    destination = Path(destination)
    with access(registry, key) as (c, trusted):
        with staged_directory(destination) as stage:
            extract(archive, stage / "payload")
            result = verify_payload(stage / "payload", trusted, key)
            shutil.copyfile(archive, stage / "checkpoint.zip")
        return result


def seal_authority(c, key):
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM authority").fetchone()
    c.execute(
        "UPDATE authority SET signature=?",
        (sign(key, {k: row[k] for k in row.keys() if k not in ("head", "signature")}),),
    )


def backup(registry, key, destination, *, transfer=False):
    """Transfer the accepted head, signed lineage, claims and cursors, never the key."""
    destination = Path(destination).resolve()
    with access(registry, key, True, allow_fenced=transfer) as (c, trusted):
        check_cursors(c, trusted, key)
        if not trusted["active"]:
            if not transfer or trusted["transfer_target"] != str(destination):
                raise ValueError(
                    "Fenced authority can only resume its original transfer"
                )
            if destination.exists():
                doc = check_signed(read_json(destination / "handoff.json"), key)
                if doc["head"] != trusted["head"] or not doc["transfer"]:
                    raise ValueError("Published transfer does not match fenced head")
                return {
                    "ok": True,
                    "test_only": bool(trusted["test_only"]),
                    "head": trusted["head"],
                    "key_included": False,
                    "source_fenced": True,
                }
        _check_destination(destination)
        if c.execute("SELECT 1 FROM batches WHERE state<>'accepted'").fetchone():
            raise ValueError(
                "Finish/recover the authorized batch before portable accepted-head backup"
            )
        row = c.execute(
            "SELECT * FROM accepted WHERE checkpoint=?", (trusted["head"],)
        ).fetchone()
        if not row:
            raise ValueError("No accepted successor to transfer")
        info = parent_info(c, trusted, key, row["path"])
        if transfer and trusted["active"]:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(
                    "UPDATE authority SET active=0,lease_epoch=lease_epoch+1,transfer_target=?",
                    (str(destination),),
                )
                seal_authority(c, key)
                c.commit()
            except BaseException:
                c.rollback()
                raise
            trusted = authority(c, key)
        with staged_directory(destination) as stage:
            with closing(sqlite3.connect(stage / "authority.sqlite")) as copy:
                c.backup(copy)
                copy.row_factory = sqlite3.Row
                if not transfer:
                    copy.execute("UPDATE authority SET active=0,transfer_target=NULL")
                    seal_authority(copy, key)
                    copy.commit()
            shutil.copyfile(
                Path(row["path"]) / "checkpoint.zip", stage / "checkpoint.zip"
            )
            write_json(
                stage / "acceptance.json", json.loads(row["proof"])["acceptance"]
            )
            write_json(
                stage / "narration.json", signed(cursor_document(c, trusted), key)
            )
            document = {
                **identity(trusted),
                "action": "portable_accepted_career",
                "head": trusted["head"],
                "transfer": transfer,
                "lease_epoch": trusted["lease_epoch"],
                "files": {
                    n: file_sha256(stage / n)
                    for n in (
                        "authority.sqlite",
                        "checkpoint.zip",
                        "acceptance.json",
                        "narration.json",
                    )
                },
            }
            write_json(stage / "handoff.json", signed(document, key))
        return {
            "ok": True,
            "test_only": bool(trusted["test_only"]),
            "head": trusted["head"],
            "key_included": False,
            "source_fenced": transfer,
        }


def restore_backup(
    source, key, destination, *, expected_test_only, recover_lost_authority=False
):
    source = Path(source)
    destination = Path(destination)
    if type(expected_test_only) is not bool:
        raise ValueError("Explicit authority mode required")
    doc = check_signed(read_json(source / "handoff.json"), key)
    if not doc.get("transfer") and not recover_lost_authority:
        raise ValueError(
            "Backup activation requires explicit lost-authority recovery; never run two writable registries"
        )
    names = {
        "authority.sqlite",
        "checkpoint.zip",
        "acceptance.json",
        "narration.json",
        "handoff.json",
    }
    if (
        set(p.name for p in source.iterdir()) != names
        or doc["profile"] != PROFILE
        or doc["action"] != "portable_accepted_career"
        or doc["test_only"] != expected_test_only
        or doc["files"]
        != {n: file_sha256(source / n) for n in names - {"handoff.json"}}
    ):
        raise ValueError("Tampered or mixed-mode portable career")
    with staged_directory(destination) as stage:
        authority_path = stage / "authority" / "career.sqlite"
        authority_path.parent.mkdir()
        shutil.copyfile(source / "authority.sqlite", authority_path)
        with access(authority_path, key) as (c, trusted):
            if (
                trusted["head"] != doc["head"]
                or bool(trusted["test_only"]) != expected_test_only
            ):
                raise ValueError("Portable registry head/mode mismatch")
            if trusted["active"] or trusted["lease_epoch"] != doc["lease_epoch"]:
                raise ValueError("Portable authority was not fenced correctly")
        checkpoint = stage / "accepted-head"
        restore(authority_path, key, source / "checkpoint.zip", checkpoint)
        acceptance = check_signed(read_json(source / "acceptance.json"), key)
        with access(authority_path, key) as (c, trusted):
            meta = read_json(checkpoint / "payload/checkpoint.json")
            if acceptance != expected_acceptance(
                meta, file_sha256(checkpoint / "checkpoint.zip"), trusted
            ):
                raise ValueError("Portable head was not separately accepted")
            c.execute(
                "UPDATE accepted SET path=? WHERE checkpoint=?",
                (str(checkpoint.resolve()), trusted["head"]),
            )
            row = c.execute(
                "SELECT * FROM batches WHERE checkpoint=?", (trusted["head"],)
            ).fetchone()
            c.execute(
                "UPDATE batches SET directory=? WHERE id=?",
                (str(checkpoint.resolve()), row["id"]),
            )
            write_json(
                checkpoint / "acceptance.json", read_json(source / "acceptance.json")
            )
            c.execute(
                "UPDATE authority SET active=1,transfer_target=NULL,lease_epoch=lease_epoch+?",
                (int(recover_lost_authority),),
            )
            seal_authority(c, key)
        import_cursor(authority_path, key, read_json(source / "narration.json"))
        with access(authority_path, key) as (c, trusted):
            c.execute(
                "UPDATE accepted SET path=? WHERE checkpoint=?",
                (str(destination.resolve() / "accepted-head"), trusted["head"]),
            )
            c.execute(
                "UPDATE batches SET directory=? WHERE id=?",
                (str(destination.resolve() / "accepted-head"), row["id"]),
            )
    registry = destination / "authority/career.sqlite"
    return {
        "ok": True,
        "registry": str(registry.resolve()),
        "accepted_parent": str((destination / "accepted-head").resolve()),
        "head": doc["head"],
        "test_only": expected_test_only,
    }
