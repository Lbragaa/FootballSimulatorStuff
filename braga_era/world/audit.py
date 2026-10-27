"""Independent world accounting, historical protection, and reversible operation journal audit."""

import json
from ..db import connect_read_only, file_sha256
from ..acceptance import catalog
from ..history import canonical_json as encode, digest, table_fingerprint
from ..migrations import rows_by_key
from .storage import tables, captured, MUTABLE_LEGACY
from .adapters import recompute_standings
from .schema import DDL, TABLES


def audit(c, parent_path, *, check_journal=True):
    from .policy import WorldPolicy

    WorldPolicy(
        **json.loads(c.execute("SELECT policy_json FROM world_info").fetchone()[0])
    ).validate()
    if file_sha256(parent_path) != catalog()["database_sha256"]:
        raise ValueError("Accepted parent hash mismatch")
    if (
        c.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
        or c.execute("PRAGMA foreign_key_check").fetchall()
    ):
        raise ValueError("SQLite integrity/foreign-key failure")
    if (
        c.execute(
            "SELECT count(*) FROM world_info WHERE scope='NONCANONICAL DEVELOPMENT TEST' AND version='braga-world-1.0.0'"
        ).fetchone()[0]
        != 1
    ):
        raise ValueError("Unsupported world profile")
    with connect_read_only(parent_path) as parent:
        import sqlite3
        from contextlib import closing

        def objects(connection):
            return {
                r[0]: tuple(r)
                for r in connection.execute(
                    "SELECT name,type,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
                )
            }

        with closing(sqlite3.connect(":memory:")) as schema:
            schema.executescript(DDL)
            if objects(c) != {**objects(parent), **objects(schema)}:
                raise ValueError("Unexpected world schema/object change")
        for table in tables(parent):
            if table not in MUTABLE_LEGACY and table_fingerprint(
                c, table
            ) != table_fingerprint(parent, table):
                raise ValueError("Protected historical table changed: " + table)
        for table in MUTABLE_LEGACY:
            old = rows_by_key(parent, table)
            current = rows_by_key(c, table)
            if table in (
                "fixtures",
                "clubs",
                "libertadores_2027_round_of_16",
                "sudamericana_2027_playoffs",
                "cdb_2027_bracket",
            ) and set(old) != set(current):
                raise ValueError("Unauthorized identity inventory change: " + table)
            for key, row in old.items():
                protected = (
                    table in ("finance_ledger", "cdb_2027_legs")
                    or table == "fixtures"
                    and row["status"] == "final"
                    or table
                    in (
                        "libertadores_2027_round_of_16",
                        "sudamericana_2027_playoffs",
                        "cdb_2027_bracket",
                    )
                    and row["status"] in ("complete", "completed", "final")
                    or table.startswith("payroll_")
                    and row["period"] != "2027-09"
                )
                if protected and current.get(key) != row:
                    raise ValueError(
                        "Previously completed record altered: " + table + " " + key
                    )
                if table == "fixtures" and row["status"] == "scheduled":
                    permitted = {
                        "status",
                        "home_goals",
                        "away_goals",
                        "home_xg",
                        "away_xg",
                        "home_shots",
                        "away_shots",
                        "home_possession",
                        "away_possession",
                        "home_sot",
                        "away_sot",
                        "report",
                    }
                    if any(current[key][k] != row[k] for k in set(row) - permitted):
                        raise ValueError("Unauthorized future fixture metadata change")
                    receipt = c.execute(
                        "SELECT 1 FROM world_receipts WHERE fixture_key=?",
                        ("league:" + str(row["id"]),),
                    ).fetchone()
                    if not receipt and current[key] != row:
                        raise ValueError("Unexecuted future fixture changed")
                if table == "clubs":
                    for col in set(row) - {
                        "points",
                        "played",
                        "wins",
                        "draws",
                        "losses",
                        "gf",
                        "ga",
                    }:
                        if row[col] != current[key][col]:
                            raise ValueError("Unauthorized club attribute change")
        old_ledger = rows_by_key(parent, "finance_ledger")
        from ..payroll import cents, obligations
        from ..state import ACCOUNT

        for key, row in rows_by_key(c, "finance_ledger").items():
            if key in old_ledger:
                continue
            period = row["dated"][:7]
            p = c.execute(
                "SELECT * FROM payroll_periods WHERE ledger_id=?", (row["id"],)
            ).fetchone()
            due = sum(r["due_cents"] for r in obligations(c, period, row["dated"]))
            if (
                not p
                or p["period"] != period
                or p["cash_cents"] != due
                or cents(row["amount_brl"]) != -due
                or row["account"] != ACCOUNT
                or row["category"] != "incremental wage payroll"
                or row["fictional"] != 1
            ):
                raise ValueError("Unauthorized financial posting")
        if check_journal:
            verify_journal(c, parent)
    for cid, stats in recompute_standings(c, False).items():
        row = c.execute("SELECT * FROM clubs WHERE id=?", (cid,)).fetchone()
        if any(row[k] != v for k, v in stats.items()):
            raise ValueError("League standings do not reconcile")
    finals = {
        r["key"]: r
        for r in c.execute("SELECT * FROM world_fixtures WHERE status='final'")
    }
    receipts = {r["fixture_key"]: r for r in c.execute("SELECT * FROM world_receipts")}
    if set(finals) != set(receipts):
        raise ValueError("Final fixture/one-time receipt mismatch")
    for key, receipt in receipts.items():
        row = c.execute(
            "SELECT * FROM world_executions WHERE fixture_key=?", (key,)
        ).fetchone()
        if (
            row["status"] != "applied"
            or digest(json.loads(row["result_json"])) != receipt["result_sha256"]
            or row["result_sha256"] != receipt["result_sha256"]
        ):
            raise ValueError("Execution/result receipt mismatch")
        b = json.loads(row["result_json"])
        f = finals[key]
        from ..engine import EngineConfig
        from .codec import snapshot, result
        from .policy import Rules, rules_for
        from .knockout import validate_bundle

        data = json.loads(row["input_json"])
        config = EngineConfig(**json.loads(row["config_json"]))
        if config != EngineConfig() or digest(data) != row["input_sha256"]:
            raise ValueError("Unsupported engine/config or changed input")
        rule = rules_for(
            f["competition"],
            f["leg"] == 2 or f["stage"] == "Final única",
            f["stage"] == "Final única",
        )
        if Rules(**data["rules"]) != rule:
            raise ValueError("Unsupported or changed competition rule policy")
        validate_bundle(
            snapshot(data["snapshot"]),
            result(b["regulation"]),
            config,
            rule,
            tuple(data["prior"]),
            b,
        )
        if [f["home_goals"], f["away_goals"]] != b["score"]:
            raise ValueError("Fixture/result score mismatch")
        stored = [
            json.loads(r[0])
            for r in c.execute(
                "SELECT event_json FROM world_events WHERE fixture_key=? ORDER BY sequence",
                (key,),
            )
        ]
        if stored != b["events"]:
            raise ValueError("Persisted event stream differs")
        perfs = [
            json.loads(r[0])
            for r in c.execute(
                "SELECT performance_json FROM world_performances WHERE fixture_key=? ORDER BY player_id",
                (key,),
            )
        ]
        if perfs != sorted(b["performances"], key=lambda p: p["player_id"]):
            raise ValueError("Persisted player statistics differ")
    for tie in c.execute("SELECT * FROM world_ties"):
        fixtures = c.execute(
            "SELECT * FROM world_fixtures WHERE tie_key=? AND status='final' ORDER BY leg",
            (tie["key"],),
        ).fetchall()
        a = b = 0
        for f in fixtures:
            x, y = (
                (f["home_goals"], f["away_goals"])
                if f["home"] == tie["club_a"]
                else (f["away_goals"], f["home_goals"])
            )
            a += x
            b += y
        if (tie["aggregate_a"], tie["aggregate_b"], tie["legs_played"]) != (
            a,
            b,
            len(fixtures),
        ):
            raise ValueError("Tie aggregate/legs mismatch")
        if tie["winner"] and (
            not fixtures
            or json.loads(fixtures[-1]["resolution_json"])["winner"] != tie["winner"]
        ):
            raise ValueError("Qualified club mismatch")
    violations = rest_inventory(c)
    return {
        "ok": True,
        "scope": "NONCANONICAL DEVELOPMENT TEST",
        "receipts": len(receipts),
        "league_final": sum(r["competition"] == "LEAGUE" for r in finals.values()),
        "continental_final": sum(
            r["competition"] in ("LIB", "SULA") for r in finals.values()
        ),
        "rest_exceptions": violations,
        "historical_tables_and_completed_rows_preserved": True,
        "journal_verified": check_journal,
    }


def verify_journal(c, parent):
    current = captured(c)
    previous = "0" * 64
    ops = []
    for seq, r in enumerate(
        c.execute("SELECT * FROM world_operations ORDER BY sequence"), 1
    ):
        op = {
            "phase": r["phase"],
            "table": r["table_name"],
            "key": json.loads(r["row_key_json"]),
            "before": json.loads(r["before_json"]) if r["before_json"] else None,
            "after": json.loads(r["after_json"]) if r["after_json"] else None,
            "previous_sha256": r["previous_sha256"],
        }
        if (
            r["sequence"] != seq
            or op["previous_sha256"] != previous
            or digest(op) != r["sha256"]
        ):
            raise ValueError("Operation journal hash/sequence mismatch")
        previous = r["sha256"]
        ops.append(op)
    for op in reversed(ops):
        table = op["table"]
        key = encode(op["key"])
        if table not in current or current[table].get(key) != op["after"]:
            raise ValueError("Operation journal after-image mismatch: " + table)
        if op["before"] is None:
            current[table].pop(key, None)
        else:
            current[table][key] = op["before"]
    for table, rows in current.items():
        expected = {} if table in TABLES else rows_by_key(parent, table)
        if rows != expected:
            raise ValueError(
                "Operation journal does not reconstruct accepted parent: " + table
            )


def rest_inventory(c):
    from .players import moment

    entries = {}
    for r in c.execute(
        "SELECT * FROM world_fixtures WHERE home IS NOT NULL ORDER BY kickoff,key"
    ):
        for key in (r["home"], r["away"]):
            entries.setdefault(key, []).append(r)
    exceptions = []
    for club, rows in entries.items():
        for a, b in zip(rows, rows[1:]):
            hours = (moment(b["kickoff"]) - moment(a["kickoff"])).total_seconds() / 3600
            if hours < 72:
                if not (
                    hours == 69 and a["competition"] == b["competition"] == "LEAGUE"
                ):
                    raise ValueError(
                        "Undisclosed sub-72h fixture interval: "
                        + a["key"]
                        + " / "
                        + b["key"]
                    )
                exceptions.append(
                    {
                        "club": club,
                        "first": a["key"],
                        "second": b["key"],
                        "hours": hours,
                        "inherited": True,
                    }
                )
    return exceptions
