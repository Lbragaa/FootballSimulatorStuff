"""Separately registered forward authorization and candidate acceptance protocol.

No CLI creates a production authority. A trusted commissioner runtime provisions
the signing key and registry explicitly. Task 03C exercises test registries only.
Approvals are HMAC receipts, not assertions in an editable execution manifest.
"""

from contextlib import closing
from functools import wraps
from inspect import signature as function_signature
from dataclasses import asdict
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3

from .acceptance import catalog
from .checkpoints import read_json, write_json
from .db import file_sha256, connect_read_only
from .history import canonical_json as encode, digest
from .world.policy import ReadinessPolicy
from .world.forward_config import ForwardConfig, configuration

PROFILE = "official-forward-profile-1"
TEST_SCOPE = "NONCANONICAL FORWARD AUTHORIZATION REHEARSAL"
OFFICIAL_SCOPE = "UNACCEPTED OFFICIAL FORWARD CANDIDATE"
REQUIRED = {
    "rosters",
    "rules_and_draws",
    "player_timeline",
    "engine_configuration",
    "specified_batch",
}


def planned_fixtures(parent, until):
    """Authorize future fixture slots without inventing their participants."""
    from .world.adapters import calendar_key

    keys = []
    with connect_read_only(parent) as c:
        keys += [
            f"league:{r[0]}"
            for r in c.execute(
                "SELECT id FROM fixtures WHERE competition='Brasileirão 2027' AND status='scheduled' AND datetime_local<=?",
                (until,),
            )
        ]
        for r in c.execute(
            "SELECT * FROM calendar_events WHERE kickoff<=? ORDER BY event_id", (until,)
        ):
            if not r["event_id"].startswith("reserve:"):
                keys.append(calendar_key(r["competition"], r["event_id"]))
            else:
                size = {"R16": 8, "QF": 4, "SF": 2, "FINAL": 1}[r["stage"]]
                keys += [
                    f"{r['competition'].lower()}:{r['stage']}-{i:02}:L{r['leg']}"
                    for i in range(1, size + 1)
                ]
    if len(keys) != len(set(keys)):
        raise ValueError("Planned fixture identity collision")
    return sorted(keys)


def sign(key, document):
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Authority key must contain at least 32 bytes")
    return hmac.new(key, encode(document).encode("utf-8"), hashlib.sha256).hexdigest()


def provision(path, key, *, test_only, commissioner):
    """Explicit local trust bootstrap; never modifies the accepted JSON registry."""
    path = Path(path)
    if path.exists() or not commissioner or type(test_only) is not bool:
        raise ValueError("Fresh explicit forward authority required")
    sign(key, {})
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents two provisioners from silently choosing keys.
    with path.open("xb"):
        pass
    with sqlite3.connect(path) as c:
        c.executescript(
            """
        CREATE TABLE authority(profile TEXT PRIMARY KEY,key_hash TEXT NOT NULL,test_only INTEGER NOT NULL,commissioner TEXT NOT NULL,parent TEXT NOT NULL);
        CREATE TABLE batches(id TEXT PRIMARY KEY,manifest TEXT NOT NULL,authorization TEXT,state TEXT NOT NULL,candidate_hash TEXT,candidate_path TEXT);
        CREATE TABLE decisions(id INTEGER PRIMARY KEY,batch TEXT NOT NULL,kind TEXT NOT NULL,document TEXT NOT NULL,signature TEXT NOT NULL);
        CREATE TABLE accepted(parent TEXT PRIMARY KEY,candidate_hash TEXT UNIQUE NOT NULL,batch TEXT UNIQUE NOT NULL);
        CREATE TABLE fixture_claims(parent TEXT NOT NULL,fixture TEXT NOT NULL,batch TEXT NOT NULL,PRIMARY KEY(parent,fixture));
        CREATE TABLE obligation_claims(parent TEXT NOT NULL,obligation TEXT NOT NULL,batch TEXT NOT NULL,PRIMARY KEY(parent,obligation));
        """
        )
        c.execute(
            "INSERT INTO authority VALUES(?,?,?,?,?)",
            (
                PROFILE,
                hashlib.sha256(key).hexdigest(),
                int(test_only),
                commissioner,
                catalog()["database_sha256"],
            ),
        )


def prepare(parent, *, until, fixtures, seed, execution_id):
    from .world.players import moment
    import calendar

    if file_sha256(parent) != catalog()["database_sha256"]:
        raise ValueError("Exact accepted parent required")
    moment(until)
    if (
        not execution_id
        or not seed
        or not fixtures
        or len(fixtures) != len(set(fixtures))
    ):
        raise ValueError("Explicit unique batch, seed and fixture inventory required")
    if sorted(fixtures) != planned_fixtures(parent, until):
        raise ValueError(
            "Preparation requires the exact chronological fixture inventory"
        )
    return {
        "profile": PROFILE,
        "parent_sha256": catalog()["database_sha256"],
        "execution_id": execution_id,
        "until": until,
        "fixtures": sorted(fixtures),
        "policy": asdict(ReadinessPolicy()),
        "obligations": [
            f"payroll:2027-{month:02}"
            for month in range(9, 13)
            if moment(f"2027-{month:02}-{calendar.monthrange(2027,month)[1]} 23:59")
            <= moment(until)
        ],
        "configuration": asdict(ForwardConfig()),
        "configurations": {
            "normal": asdict(configuration(ReadinessPolicy())),
            "neutral_final": asdict(configuration(ReadinessPolicy(), True)),
        },
        "engine_version": ForwardConfig().version,
        "seed": f"official-forward:{execution_id}:{seed}",
        "required_decisions": sorted(REQUIRED),
        "acceptance": "separate exact-hash promotion decision required",
    }


def authority(c, key):
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM authority").fetchone()
    if (
        not row
        or row["profile"] != PROFILE
        or row["parent"] != catalog()["database_sha256"]
        or not hmac.compare_digest(row["key_hash"], hashlib.sha256(key).hexdigest())
    ):
        raise ValueError("Untrusted forward authority/key/parent")
    return row


def validate_authorization(c, key, trusted, manifest):
    row = c.execute(
        "SELECT * FROM decisions WHERE batch=? AND kind='execution'",
        (manifest["execution_id"],),
    ).fetchone()
    expected = {
        "action": "authorize_execution",
        "manifest_sha256": digest(manifest),
        "approvals": sorted(REQUIRED),
        "commissioner": trusted["commissioner"],
        "test_only": bool(trusted["test_only"]),
    }
    if (
        not row
        or json.loads(row["document"]) != expected
        or not hmac.compare_digest(row["signature"], sign(key, expected))
    ):
        raise ValueError("Execution authorization signature/manifest mismatch")
    claims = [
        r[0]
        for r in c.execute(
            "SELECT fixture FROM fixture_claims WHERE parent=? AND batch=? ORDER BY fixture",
            (manifest["parent_sha256"], manifest["execution_id"]),
        )
    ]
    if claims != manifest["fixtures"]:
        raise ValueError("Execution fixture claims differ from authorization")
    return expected


def authorize(registry, key, manifest, decision, signature):
    """Approval of software or a roster alone cannot authorize execution."""
    with closing(sqlite3.connect(registry, isolation_level=None, timeout=0)) as c:
        trusted = authority(c, key)
        expected = {
            "action": "authorize_execution",
            "manifest_sha256": digest(manifest),
            "approvals": sorted(REQUIRED),
            "commissioner": trusted["commissioner"],
            "test_only": bool(trusted["test_only"]),
        }
        if decision != expected or not hmac.compare_digest(
            sign(key, decision), signature
        ):
            raise ValueError("Wrong, incomplete or unsigned execution authorization")
        if (
            manifest["profile"] != PROFILE
            or manifest["parent_sha256"] != trusted["parent"]
            or manifest["policy"] != asdict(ReadinessPolicy())
            or manifest["configuration"] != asdict(ForwardConfig())
            or manifest.get("configurations")
            != {
                "normal": asdict(configuration(ReadinessPolicy())),
                "neutral_final": asdict(configuration(ReadinessPolicy(), True)),
            }
        ):
            raise ValueError("Unsupported forward profile/model/policy")
        c.execute("BEGIN IMMEDIATE")
        try:
            if any(
                json.loads(r[0])["seed"] == manifest["seed"]
                for r in c.execute("SELECT manifest FROM batches")
            ):
                raise ValueError("Execution seed namespace already committed")
            c.execute(
                "INSERT INTO batches VALUES(?,?,?,'authorized',NULL,NULL)",
                (manifest["execution_id"], encode(manifest), encode(decision)),
            )
            c.executemany(
                "INSERT INTO fixture_claims VALUES(?,?,?)",
                [
                    (manifest["parent_sha256"], fixture, manifest["execution_id"])
                    for fixture in manifest["fixtures"]
                ],
            )
            c.executemany(
                "INSERT INTO obligation_claims VALUES(?,?,?)",
                [
                    (manifest["parent_sha256"], item, manifest["execution_id"])
                    for item in manifest["obligations"]
                ],
            )
            c.execute(
                "INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)",
                (manifest["execution_id"], "execution", encode(decision), signature),
            )
            c.commit()
        except BaseException:
            c.rollback()
            raise


def scoped(function):
    @wraps(function)
    def call(*args, **kwargs):
        arguments = function_signature(function).bind(*args, **kwargs).arguments
        registry = Path(arguments["registry"]).resolve()
        if not registry.is_file():
            raise ValueError("Missing forward authority registry")
        with closing(sqlite3.connect(registry.as_uri() + "?mode=ro", uri=True)) as c:
            trusted = authority(c, arguments["key"])
        from .world.scope import calculation

        with calculation(bool(trusted["test_only"])):
            return function(*args, **kwargs)

    return call


@scoped
def execute(registry, key, execution_id, directory, parent, *, crash=None):
    """Once-only/resumable execution; production use needs a signed batch decision.

    Calculation copies remain unaccepted and isolated. Their DEV package cannot
    be promoted; only this independently validated registered wrapper can enter
    the separate forward acceptance registry.
    """
    from .world.storage import create, process_lock
    from .world.runner import advance
    from .world.packages import export_world, verify_directory, fingerprints

    directory = Path(directory).resolve()
    registry = Path(registry).resolve()
    with closing(sqlite3.connect(registry, isolation_level=None, timeout=0)) as c:
        trusted = authority(c, key)
        row = c.execute("SELECT * FROM batches WHERE id=?", (execution_id,)).fetchone()
        if not row or row["state"] not in ("authorized", "executing", "candidate"):
            raise ValueError(
                "Batch lacks execution authorization or is already accepted"
            )
        manifest = json.loads(row["manifest"])
        approved = validate_authorization(c, key, trusted, manifest)
        if json.loads(row["authorization"]) != approved:
            raise ValueError("Stored batch authorization differs from signed decision")
        if file_sha256(parent) != manifest["parent_sha256"]:
            raise ValueError("Parent mismatch")
        # All registry state transitions use the same crash-released process lock.
        with process_lock(registry.parent):
            if row["candidate_path"] and Path(row["candidate_path"]) != directory:
                raise ValueError("Resume the original execution directory")
            if row["state"] == "candidate":
                return verify_candidate(directory, registry, key)
            c.execute(
                "UPDATE batches SET state='executing',candidate_path=? WHERE id=?",
                (str(directory), execution_id),
            )
            world = directory / "calculation"
            if not world.exists():
                directory.mkdir(parents=True, exist_ok=True)
                create(parent, world, manifest["seed"], ReadinessPolicy())
            with connect_read_only(world / "database.sqlite") as w:
                info = w.execute("SELECT seed,policy_json FROM world_info").fetchone()
                if (
                    info[0] != manifest["seed"]
                    or json.loads(info[1]) != manifest["policy"]
                ):
                    raise ValueError("Resumed calculation differs from authorization")
                requested = planned_fixtures(parent, manifest["until"])
                if requested != manifest["fixtures"]:
                    raise ValueError(
                        "Authorization does not cover the exact chronological fixture batch"
                    )
            report = advance(world, until=manifest["until"], crash=crash)
            with connect_read_only(world / "database.sqlite") as w:
                receipts = [
                    r[0]
                    for r in w.execute(
                        "SELECT fixture_key FROM world_receipts ORDER BY fixture_key"
                    )
                ]
                if receipts != manifest["fixtures"]:
                    raise ValueError(
                        "Authorized batch is incomplete or contains extra executions"
                    )
                paid = [
                    r[0]
                    for r in w.execute(
                        "SELECT key FROM world_obligations WHERE status='paid' ORDER BY key"
                    )
                ]
                if paid != manifest["obligations"]:
                    raise ValueError(
                        "Authorized administrative obligation inventory differs"
                    )
                world_hash = digest(fingerprints(w))
            archive = directory / "successor-calculation.zip"
            if not archive.exists():
                export_world(world, archive)
            # The wrapper is a distinct registered candidate, never DEV renamed to 047.
            candidate = {
                "profile": PROFILE,
                "scope": TEST_SCOPE if trusted["test_only"] else OFFICIAL_SCOPE,
                "test_only": bool(trusted["test_only"]),
                "acceptance_eligible": not bool(trusted["test_only"]),
                "manifest": manifest,
                "authorization": json.loads(row["authorization"]),
                "calculation_archive_sha256": file_sha256(archive),
                "world_sha256": world_hash,
                "receipt_inventory": receipts,
            }
            write_json(directory / "forward_candidate.json", candidate)
            c.execute(
                "UPDATE batches SET state='candidate',candidate_hash=? WHERE id=?",
                (digest(candidate), execution_id),
            )
            return verify_candidate(directory, registry, key)


@scoped
def verify_candidate(directory, registry, key):
    from .checkpoints import verify_archive

    directory = Path(directory)
    candidate = read_json(directory / "forward_candidate.json")
    with closing(sqlite3.connect(registry)) as c:
        trusted = authority(c, key)
        row = c.execute(
            "SELECT * FROM batches WHERE id=?", (candidate["manifest"]["execution_id"],)
        ).fetchone()
        if (
            not row
            or row["candidate_hash"] != digest(candidate)
            or candidate["manifest"] != json.loads(row["manifest"])
            or candidate["test_only"] != bool(trusted["test_only"])
        ):
            raise ValueError("Forward candidate differs from authorized registry")
        receipt = c.execute(
            "SELECT * FROM decisions WHERE batch=? AND kind='execution'", (row["id"],)
        ).fetchone()
        approved = validate_authorization(c, key, trusted, candidate["manifest"])
        if (
            candidate["authorization"] != approved
            or json.loads(row["authorization"]) != approved
        ):
            raise ValueError("Candidate authorization differs from signed decision")
        if not receipt or not hmac.compare_digest(
            receipt["signature"], sign(key, json.loads(receipt["document"]))
        ):
            raise ValueError("Authorization receipt signature mismatch")
    archive = directory / "successor-calculation.zip"
    if file_sha256(archive) != candidate["calculation_archive_sha256"]:
        raise ValueError("Forward successor archive changed")
    verified = verify_archive(archive)
    if (
        verified["metadata"]["world_sha256"] != candidate["world_sha256"]
        or verified["metadata"]["parent_sha256"]
        != candidate["manifest"]["parent_sha256"]
    ):
        raise ValueError("Independent forward restoration differs")
    return {
        "ok": True,
        "candidate_sha256": digest(candidate),
        "scope": candidate["scope"],
        "test_only": candidate["test_only"],
        "independent_restoration": True,
        "promotion_required": True,
    }


@scoped
def promote(directory, registry, key, decision, signature):
    """Final exact candidate acceptance, never implied by execution permission."""
    verified = verify_candidate(directory, registry, key)
    candidate = read_json(Path(directory) / "forward_candidate.json")
    with closing(sqlite3.connect(registry, isolation_level=None, timeout=0)) as c:
        trusted = authority(c, key)
        expected = {
            "action": "accept_forward_candidate",
            "candidate_sha256": verified["candidate_sha256"],
            "parent_sha256": trusted["parent"],
            "commissioner": trusted["commissioner"],
            "test_only": bool(trusted["test_only"]),
        }
        if decision != expected or not hmac.compare_digest(
            signature, sign(key, decision)
        ):
            raise ValueError("Separate exact-hash acceptance decision required")
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute(
                "INSERT INTO accepted VALUES(?,?,?)",
                (
                    trusted["parent"],
                    verified["candidate_sha256"],
                    candidate["manifest"]["execution_id"],
                ),
            )
            c.execute(
                "UPDATE batches SET state='accepted' WHERE id=? AND state='candidate'",
                (candidate["manifest"]["execution_id"],),
            )
            c.execute(
                "INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)",
                (
                    candidate["manifest"]["execution_id"],
                    "acceptance",
                    encode(decision),
                    signature,
                ),
            )
            c.commit()
        except BaseException:
            c.rollback()
            raise
    return {
        "accepted_in_separate_registry": True,
        "test_only": bool(trusted["test_only"]),
        "candidate_sha256": verified["candidate_sha256"],
    }


@scoped
def gameplay(registry, key, execution_id, command, fixture=None, count=1):
    """The explicit trusted bridge; generic DEV packages never gain authority."""
    from .gameplay import handoff

    with closing(sqlite3.connect(registry)) as c:
        trusted = authority(c, key)
        row = c.execute("SELECT * FROM batches WHERE id=?", (execution_id,)).fetchone()
        if not row or row["state"] not in ("candidate", "accepted"):
            raise ValueError("No validated forward candidate for gameplay")
        verified = verify_candidate(row["candidate_path"], registry, key)
        value = handoff(
            Path(row["candidate_path"]) / "calculation", command, fixture, count
        )
        value.update(
            scope=verified["scope"],
            test_only=bool(trusted["test_only"]),
            accepted=row["state"] == "accepted",
            profile=PROFILE,
        )
        return value
