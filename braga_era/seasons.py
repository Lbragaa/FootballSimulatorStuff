"""Nonpromotable season-lifecycle rehearsals. No official writer or activation API.

The inherited database is an immutable archive, not migrated by this milestone.
New workflow records live in a separate, explicitly development-only database.
"""

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import sqlite3

from .acceptance import catalog
from .checkpoints import staged_directory, write_json, read_json
from .db import connect_read_only, file_sha256
from .history import canonical_json, digest, table_fingerprint
from .results import Projection

PROFILE = "DEV-SEASON-LIFECYCLE-1"
SCOPE = "NONCANONICAL DEVELOPMENT TEST - NEVER PROMOTE"
STATES = ("season_in_progress", "season_finalizing", "season_archived",
          "offseason_preparation", "transfer_window", "preseason", "next_season_ready")
DDL = """
CREATE TABLE season_cycles(season INTEGER PRIMARY KEY, next_season INTEGER NOT NULL UNIQUE,
 state TEXT NOT NULL, policy_sha256 TEXT NOT NULL);
CREATE TABLE season_transitions(request_id TEXT PRIMARY KEY, season INTEGER NOT NULL REFERENCES season_cycles(season),
 input_sha256 TEXT NOT NULL, report_json TEXT NOT NULL, previous_sha256 TEXT NOT NULL, sha256 TEXT NOT NULL);
CREATE TABLE season_archives(season INTEGER PRIMARY KEY REFERENCES season_cycles(season),
 manifest_json TEXT NOT NULL, sha256 TEXT NOT NULL);
"""


@dataclass(frozen=True)
class AcceptedSource:
    database: Path
    checkpoint: str
    database_sha256: str

    @classmethod
    def root(cls, database):
        path = Path(database).resolve()
        expected = catalog()["database_sha256"]
        if file_sha256(path) != expected:
            raise ValueError("Exact accepted root bytes required")
        return cls(path, expected, expected)

    @classmethod
    def career(cls, career):
        """Authenticate the registered CURRENT parent without changing authority."""
        from . import lineage
        head = career.identity()["checkpoint"]
        with lineage.access(career.registry, career.key) as (c, trusted):
            parent = getattr(career, "root_parent", None) if head == lineage.ROOT else Path(
                c.execute("SELECT path FROM accepted WHERE checkpoint=?", (head,)).fetchone()[0])
            if parent is None:
                raise ValueError("Authenticated accepted root installation required")
            info = lineage.parent_info(c, trusted, career.key, parent)
        return cls(Path(info["database"]), info["checkpoint"], file_sha256(info["database"]))


def fingerprints(c):
    return {r[0]: table_fingerprint(c, r[0]) for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")}


def source_manifest(path):
    with connect_read_only(path) as c:
        return {"database_sha256": file_sha256(Path(path)), "tables": fingerprints(c),
                "schema_sha256": digest([list(r) for r in c.execute(
                    "SELECT name,type,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name")])}


def validate_policy(policy):
    """Closed proposed policy; no claim that review constitutes match authority."""
    if (not isinstance(policy, dict) or set(policy) != {"version", "season", "next_season", "competitions"}
        or policy["version"] != "season-lifecycle-proposal-1"
        or type(policy["season"]) is not int or not 1900 <= policy["season"] < 2200
        or type(policy["next_season"]) is not int or policy["next_season"] != policy["season"] + 1
        or not isinstance(policy["competitions"], list) or not policy["competitions"]):
        raise ValueError("Unsupported season policy")
    keys = set()
    for spec in policy["competitions"]:
        if (not isinstance(spec, dict) or set(spec) != {"id", "minimum_completed", "cross_year", "requires_champion"}
            or not isinstance(spec["id"], str) or not spec["id"] or spec["id"] in keys
            or type(spec["minimum_completed"]) is not int or spec["minimum_completed"] < 1
            or type(spec["cross_year"]) is not bool or type(spec["requires_champion"]) is not bool):
            raise ValueError("Invalid or duplicate competition closure policy")
        keys.add(spec["id"])


def closure_report(database, policy):
    """PRIVATE diagnostic counts only; no scores, champions' names or future news.

    A missing competition is a blocker, not evidence of an empty completed season.
    Actual dates never assign a season. Cross-year competitions retain all pending
    identities in the report and are excluded ONLY by explicit policy scope.
    """
    validate_policy(policy)
    with connect_read_only(database) as c:
        projection = Projection(c)
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        champs = {r[0] for r in c.execute("SELECT competition FROM world_champions")} if "world_champions" in tables else set()
        blockers, competitions, carried = [], [], []
        for spec in policy["competitions"]:
            rows = [r for r in projection.records.values() if r["competition_id"] == spec["id"] and r["season"] == policy["season"]]
            # Activated reservations are already removed by the shared projection.
            pending = [r["id"] for r in rows if r["status"] != "completed"]
            completed = sum(r["status"] == "completed" for r in rows)
            missing_scores = sum(r["status"] == "completed" and r.get("score_availability") == "not_recorded" for r in rows)
            has_champion = spec["id"] in champs or any(
                t["competition_id"] == spec["id"] and t["season"] == policy["season"]
                and t["stage"] == "FINAL" and t["qualified"] for t in projection.ties.values())
            # Legacy finals are decisions recorded by competition_history, not inferred scores.
            if "competition_history" in tables:
                from .results import competition
                has_champion = has_champion or any(competition(r["competition"])[0] == spec["id"] and r["winner"] is not None
                    for r in c.execute("SELECT * FROM competition_history WHERE season=?", (policy["season"],)))
            item = {"competition": spec["id"], "recorded": len(rows), "completed": completed,
                    "pending": pending, "missing_scores": missing_scores, "champion_recorded": bool(has_champion)}
            competitions.append(item)
            if spec["cross_year"]:
                carried.append(item)
                if not rows:
                    blockers.append("missing_cross_year_inventory:" + spec["id"])
            elif pending or completed < spec["minimum_completed"] or missing_scores or spec["requires_champion"] and not has_champion:
                blockers.append("competition_not_closed:" + spec["id"])
        # Never silently ignore another recorded competition in this same season.
        unscoped = sorted({r["competition_id"] for r in projection.records.values() if r["season"] == policy["season"]}
                          - {s["id"] for s in policy["competitions"]})
        blockers.extend("unscoped_competition:" + k for k in unscoped)
        obligations = [r[0] for r in c.execute("SELECT key FROM world_obligations WHERE status<>'paid' AND substr(kickoff,1,4)=? ORDER BY key",
                       (str(policy["season"]),))] if "world_obligations" in tables else ["missing_world_obligation_inventory"]
        if obligations:
            blockers.append("administrative_obligations_pending")
        if "world_batches" in tables and c.execute("SELECT 1 FROM world_batches WHERE status<>'applied' LIMIT 1").fetchone():
            blockers.append("incomplete_execution_commitment")
        # Only the existing 2027 champion register has unambiguous season ownership.
        if policy["season"] != 2027 and "world_champions" in tables:
            blockers.append("legacy_champion_register_not_season_scoped")
        return {"ready_to_finalize": not blockers, "season": policy["season"], "competitions": competitions,
                "carried_cross_year": carried, "pending_obligations": obligations, "blockers": blockers}


def create_rehearsal(source, directory, policy):
    """Copy an authenticated parent; create NO authority, key, worker or save profile."""
    validate_policy(policy)
    if not isinstance(source, AcceptedSource) or file_sha256(source.database) != source.database_sha256:
        raise ValueError("Authenticated source changed")
    with staged_directory(Path(directory)) as staging:
        shutil.copyfile(source.database, staging / "parent.sqlite")
        baseline = source_manifest(staging / "parent.sqlite")
        if baseline["database_sha256"] != source.database_sha256:
            raise ValueError("Parent changed while copying")
        write_json(staging / "rehearsal.json", {"profile": PROFILE, "scope": SCOPE, "acceptance_eligible": False,
                   "parent_checkpoint": source.checkpoint, "parent": baseline, "policy": policy})
        with closing(sqlite3.connect(staging / "season.sqlite")) as c:
            c.execute("PRAGMA foreign_keys=ON")
            c.executescript(DDL)
            c.execute("INSERT INTO season_cycles VALUES(?,?,?,?)", (policy["season"], policy["next_season"], STATES[0], digest(policy)))
            c.commit()
    return inspect_rehearsal(directory)


def _marker(directory):
    directory = Path(directory).resolve()
    marker = read_json(directory / "rehearsal.json")
    if marker.get("profile") != PROFILE or marker.get("scope") != SCOPE or marker.get("acceptance_eligible") is not False:
        raise ValueError("Only nonpromotable season rehearsals are supported")
    validate_policy(marker["policy"])
    if source_manifest(directory / "parent.sqlite") != marker["parent"]:
        raise ValueError("Inherited season/history was altered")
    # Backup gives the multi-table verifier one coherent snapshot even while an
    # independent rehearsal process commits its next transition.
    with connect_read_only(directory / "season.sqlite") as c, closing(sqlite3.connect(":memory:")) as snapshot:
        snapshot.row_factory = sqlite3.Row
        c.backup(snapshot)
        validate_sidecar(snapshot, marker)
    return directory, marker


def validate_sidecar(c, marker):
    """Rebuild the workflow from its complete ordered journal, independently."""
    policy = marker["policy"]
    cycles = c.execute("SELECT * FROM season_cycles").fetchall()
    if (len(cycles) != 1 or cycles[0]["season"] != policy["season"]
        or cycles[0]["next_season"] != policy["next_season"]
        or cycles[0]["policy_sha256"] != digest(policy)):
        raise ValueError("Season cycle/policy mismatch")
    previous, state = "0" * 64, STATES[0]
    for row in c.execute("SELECT * FROM season_transitions ORDER BY rowid"):
        report = json.loads(row["report_json"])
        request = {"target": report["after"], "policy_sha256": digest(policy), "parent": marker["parent_checkpoint"]}
        if (row["season"] != policy["season"] or report["request_id"] != row["request_id"]
            or report["before"] != state or STATES.index(state) + 1 >= len(STATES)
            or report["after"] != STATES[STATES.index(state) + 1]
            or report["parent"] != marker["parent_checkpoint"] or report["policy_sha256"] != digest(policy)
            or row["input_sha256"] != digest(request) or row["previous_sha256"] != previous
            or row["sha256"] != digest({"previous": previous, "request": request, "report": report})):
            raise ValueError("Season transition journal mismatch")
        previous, state = row["sha256"], report["after"]
    if cycles[0]["state"] != state:
        raise ValueError("Season state differs from transition journal")
    archives = c.execute("SELECT * FROM season_archives").fetchall()
    if len(archives) != int(STATES.index(state) >= STATES.index("season_archived")):
        raise ValueError("Missing or unexpected season archive")
    for row in archives:
        archive = json.loads(row["manifest_json"])
        if (row["season"] != policy["season"] or archive["season"] != row["season"]
            or archive["parent"] != marker["parent_checkpoint"] or archive["snapshot"] != marker["parent"]
            or digest(archive) != row["sha256"]):
            raise ValueError("Season archive provenance mismatch")


def inspect_rehearsal(directory):
    directory, marker = _marker(directory)
    with connect_read_only(directory / "season.sqlite") as c:
        row = c.execute("SELECT * FROM season_cycles").fetchone()
        return {"profile": PROFILE, "acceptance_eligible": False, "season": row["season"], "state": row["state"],
                "next_season": row["next_season"], "parent_checkpoint": marker["parent_checkpoint"],
                "closure": closure_report(directory / "parent.sqlite", marker["policy"])}


def transition(directory, target, *, request_id, crash=None):
    """Transactional exact retries in the DEV sidecar; activation intentionally absent."""
    from uuid import UUID
    if str(UUID(request_id)) != request_id or target not in STATES:
        raise ValueError("Canonical request UUID and supported rehearsal state required; activation is unavailable")
    directory, marker = _marker(directory)
    request = {"target": target, "policy_sha256": digest(marker["policy"]), "parent": marker["parent_checkpoint"]}
    with closing(sqlite3.connect(directory / "season.sqlite", timeout=1)) as c:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("BEGIN IMMEDIATE")
        try:
            validate_sidecar(c, marker)
            old = c.execute("SELECT * FROM season_transitions WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["input_sha256"] != digest(request):
                    raise ValueError("Request UUID already bound to a different transition")
                return json.loads(old["report_json"])
            cycle = c.execute("SELECT * FROM season_cycles").fetchone()
            if cycle["policy_sha256"] != digest(marker["policy"]):
                raise ValueError("Policy commitment changed")
            index = STATES.index(cycle["state"])
            if index + 1 >= len(STATES) or target != STATES[index + 1]:
                raise ValueError("Transition must follow the exact next lifecycle state")
            if target in {"transfer_window", "preseason", "next_season_ready"}:
                raise ValueError("Next-season generation/registration and financial validation are not implemented; rehearsal stops at offseason_preparation")
            closure = closure_report(directory / "parent.sqlite", marker["policy"])
            if not closure["ready_to_finalize"]:
                raise ValueError("Season cannot close: " + ", ".join(closure["blockers"]))
            report = {"request_id": request_id, "profile": PROFILE, "season": cycle["season"],
                      "before": cycle["state"], "after": target, "parent": marker["parent_checkpoint"],
                      "inherited_tables_unchanged": True, "policy_sha256": cycle["policy_sha256"],
                      "closure": closure, "acceptance_eligible": False, "next_season_generated": False}
            if target == "season_archived":
                # The entire parent.sqlite remains the archive of ALL available facts,
                # including statistics, finances, medical and manager/narrative history.
                # Missing awards/coaching observations are never fabricated.
                archive = {"season": cycle["season"], "parent": marker["parent_checkpoint"],
                           "snapshot": marker["parent"], "carried_cross_year": closure["carried_cross_year"],
                           "coverage": "all recorded tables; missing observations remain unknown"}
                c.execute("INSERT INTO season_archives VALUES(?,?,?)", (cycle["season"], canonical_json(archive), digest(archive)))
            c.execute("UPDATE season_cycles SET state=? WHERE season=?", (target, cycle["season"]))
            previous = c.execute("SELECT sha256 FROM season_transitions ORDER BY rowid DESC LIMIT 1").fetchone()
            previous = previous[0] if previous else "0" * 64
            c.execute("INSERT INTO season_transitions VALUES(?,?,?,?,?,?)", (request_id, cycle["season"], digest(request),
                      canonical_json(report), previous, digest({"previous": previous, "request": request, "report": report})))
            if crash == "before_commit":
                raise RuntimeError("Injected season crash before commit")
            c.commit()
            if crash == "after_commit":
                raise RuntimeError("Injected season crash after commit")
            return report
        except BaseException:
            c.rollback()
            raise


def double_round_robin(clubs, *, season, competition="LEAGUE", policy="berger-draft-1"):
    """Pure undated draft; qualification/calendar approval are separate prerequisites.

    Fixed input identities, no random draws and no fixture execution. Circle method
    produces each ordered pair once. Dates are deliberately not guessed.
    """
    if (policy != "berger-draft-1" or type(season) is not int or not 1900 <= season <= 2200
        or not isinstance(competition, str) or not competition.isalnum()
        or not isinstance(clubs, (list, tuple)) or not all(isinstance(k, str) and k for k in clubs)
        or len(clubs) < 4 or len(clubs) % 2 or len(set(clubs)) != len(clubs)):
        raise ValueError("Even distinct participant identities and supported draft policy required")
    rotation, first = sorted(clubs), []
    for index in range(len(clubs) - 1):
        for j in range(len(clubs) // 2):
            home, away = rotation[j], rotation[-1-j]
            if (index + j) % 2:
                home, away = away, home
            first.append({"round": index + 1, "home": home, "away": away})
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    rows = first + [{"round": r["round"] + len(clubs) - 1, "home": r["away"], "away": r["home"]} for r in first]
    return [{**r, "key": f"{competition}:{season}:R{r['round']:02}:{r['home']}:{r['away']}",
             "season": season, "policy": policy, "status": "undated_draft", "kickoff": None} for r in rows]
