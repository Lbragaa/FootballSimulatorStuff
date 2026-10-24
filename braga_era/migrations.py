"""Explicit administrative migration on scratch connections, never on the parent."""
from __future__ import annotations

import json

from .history import canonical_json, digest, quote_identifier
from .payroll import POLICY, POLICY_ID, book_payroll, cents, financial_statement, obligations
from .state import ACCOUNT

SCHEMA_VERSION = 1
MIGRATION_ID = "046_to_046C_admin_v1"
DDL = [
    """CREATE TABLE checkpoint_info (version TEXT PRIMARY KEY, parent_version TEXT NOT NULL,
        parent_sha256 TEXT NOT NULL, schema_version INTEGER NOT NULL, status TEXT NOT NULL CHECK(status='candidate'),
        profile TEXT NOT NULL, plan_sha256 TEXT NOT NULL)""",
    """CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, migration_id TEXT NOT NULL UNIQUE,
        ddl_sha256 TEXT NOT NULL)""",
    """CREATE TABLE admin_operations (sequence INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
        table_name TEXT NOT NULL, row_key_json TEXT NOT NULL, before_json TEXT, after_json TEXT,
        reason TEXT NOT NULL)""",
    """CREATE TABLE calendar_events (event_id TEXT PRIMARY KEY, competition TEXT NOT NULL,
        stage TEXT NOT NULL, leg INTEGER NOT NULL, clubs_json TEXT NOT NULL, depends_json TEXT NOT NULL,
        kickoff TEXT NOT NULL, international INTEGER NOT NULL, source_table TEXT, source_key TEXT,
        source_column TEXT, previous_date TEXT, home TEXT, away TEXT,
        status TEXT NOT NULL CHECK(status IN ('scheduled','reserved')))""",
    """CREATE TABLE admin_policies (policy_id TEXT PRIMARY KEY, policy_json TEXT NOT NULL)""",
    """CREATE TABLE payroll_periods (period TEXT PRIMARY KEY, account TEXT NOT NULL,
        policy_id TEXT NOT NULL REFERENCES admin_policies(policy_id), status TEXT NOT NULL,
        amount_due_cents INTEGER NOT NULL CHECK(amount_due_cents>=0), accrued_cents INTEGER NOT NULL CHECK(accrued_cents>=0),
        cash_cents INTEGER NOT NULL CHECK(cash_cents>=0), ledger_id INTEGER UNIQUE REFERENCES finance_ledger(id))""",
    """CREATE TABLE payroll_obligations (period TEXT NOT NULL REFERENCES payroll_periods(period),
        player_id INTEGER NOT NULL REFERENCES players(id), covered_from TEXT NOT NULL, covered_to TEXT NOT NULL,
        monthly_cents INTEGER NOT NULL, due_cents INTEGER NOT NULL, accrued_cents INTEGER NOT NULL,
        PRIMARY KEY(period,player_id))""",
]
ADDED_TABLES = {"checkpoint_info", "schema_migrations", "admin_operations", "calendar_events",
                "admin_policies", "payroll_periods", "payroll_obligations"}
CHANGED_LEGACY_TABLES = {"meta", "board_objectives", "finance_ledger", "cdb_2027_bracket",
                         "cdb_2027_plan_meta", "libertadores_2027_round_of_16", "libertadores_2027_meta",
                         "sudamericana_2027_playoffs"}


def rows_by_key(c, table):
    info = list(c.execute(f"PRAGMA table_info({quote_identifier(table)})"))
    keys = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
    if not keys:
        raise ValueError(f"No stable row key for {table}")
    rows = {}
    for row in c.execute(f"SELECT * FROM {quote_identifier(table)}"):
        value = dict(row)
        rows[canonical_json({k: value[k] for k in keys})] = value
    return rows


def capture(c, extra_tables=()):
    return {t: rows_by_key(c, t) for t in sorted(CHANGED_LEGACY_TABLES | set(extra_tables) | (ADDED_TABLES-{"admin_operations"}))
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()}


def diff(before, after):
    operations = []
    for table in sorted(set(before) | set(after)):
        previous, current = before.get(table, {}), after.get(table, {})
        for key in sorted(set(previous) | set(current)):
            if previous.get(key) != current.get(key):
                reason = ("Controlled future league kickoff adjustment; completed history and Mirassol-Vasco protected" if table == "fixtures"
                    else "Deterministic calendar reconciliation / conditional downstream capacity" if table in {
                    "calendar_events", "cdb_2027_bracket", "libertadores_2027_round_of_16", "sudamericana_2027_playoffs"}
                    else "Contract-backed incremental payroll policy / arrears and accrued liability" if table.startswith("payroll_") or table == "finance_ledger"
                    else "Evidence-backed administrative checkpoint reconciliation")
                op = {"table": table, "key": json.loads(key), "before": previous.get(key), "after": current.get(key), "reason": reason}
                operations.append({"operation_id": digest(op), **op})
    return operations


def apply(c, plan, parent_sha256: str, fail_after: str | None = None, *, revision="v1") -> list[dict]:
    """One transaction including DDL and logs; caller supplies only a scratch DB."""
    if c.in_transaction:
        raise ValueError("Migration requires an idle scratch connection")
    if dict(c.execute("SELECT key,value FROM meta")).get("saved_state_version") != "046":
        raise ValueError("Migration accepts only Save 046")
    if revision not in ("v1","v2"):
        raise ValueError("Unknown administrative revision")
    extra = ("fixtures",) if revision == "v2" else ()
    profile = "046_to_046C_admin_v2" if revision == "v2" else MIGRATION_ID
    before = capture(c, extra)
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("BEGIN IMMEDIATE")
    try:
        for statement in DDL:
            c.execute(statement)
        c.execute("INSERT INTO schema_migrations VALUES(?,?,?)", (SCHEMA_VERSION, profile, digest(DDL)))
        c.execute("INSERT INTO checkpoint_info VALUES(?,?,?,?,?,?,?)",
                  ("046C", "046", parent_sha256, SCHEMA_VERSION, "candidate", profile, digest(plan)))
        c.execute("INSERT INTO admin_policies VALUES(?,?)", ("calendar_"+revision, canonical_json(plan["policy"])))
        c.execute("INSERT INTO admin_policies VALUES(?,?)", (POLICY_ID, canonical_json(POLICY)))
        for event in plan["events"]:
            if event["source_table"]:
                table = event["source_table"]
                key_column = "tie_code" if table == "cdb_2027_bracket" else "tie_id"
                column = event["source_column"]
                cur = c.execute(f"UPDATE {quote_identifier(table)} SET {quote_identifier(column)}=? WHERE {key_column}=? AND {quote_identifier(column)}=?",
                                (event["kickoff"][:10], event["source_key"], event["previous_date"]))
                if cur.rowcount != 1:
                    raise ValueError(f"Calendar parent conflict: {event['event_id']}")
            c.execute("INSERT INTO calendar_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                event["event_id"], event["competition"], event["stage"], event["leg"], canonical_json(event["clubs"]),
                canonical_json(event["depends"]), event["kickoff"], int(event["international"]), event["source_table"],
                event["source_key"], event["source_column"], event["previous_date"], event["home"], event["away"],
                "scheduled" if event["home"] and event["away"] else "reserved"))
        if revision == "v2":
            for move in plan.get("league_adjustments",[]):
                row = c.execute("""SELECT f.*,h.name home,a.name away FROM fixtures f JOIN clubs h ON h.id=f.home_id
                    JOIN clubs a ON a.id=f.away_id WHERE f.id=?""", (move["fixture_id"],)).fetchone()
                if (not row or row["competition"] != "Brasileirão 2027" or row["status"] != "scheduled"
                        or row["datetime_local"] != move["before"] or
                        (row["round"] == "R26" and row["home"] == "Mirassol" and row["away"] == "Vasco")):
                    raise ValueError("League adjustment conflicts with protected parent fixture")
                c.execute("UPDATE fixtures SET datetime_local=? WHERE id=?",(move["after"],move["fixture_id"]))
        if fail_after == "calendar":
            raise RuntimeError("Injected failure after calendar")
        for row in c.execute("SELECT * FROM finance_ledger WHERE account=? AND category='incremental wage payroll' ORDER BY id", (ACCOUNT,)).fetchall():
            period = row["dated"][:7]
            amount = -cents(row["amount_brl"])
            c.execute("INSERT INTO payroll_periods VALUES(?,?,?,?,?,?,?,?)",
                      (period, ACCOUNT, POLICY_ID, "legacy_paid", amount, amount, amount, row["id"]))
        now = dict(c.execute("SELECT key,value FROM meta"))["current_date"]
        for period in ("2027-08", "2027-09"):
            entries = obligations(c, period, now)
            due, accrued = sum(e["due_cents"] for e in entries), sum(e["accrued_cents"] for e in entries)
            c.execute("INSERT INTO payroll_periods VALUES(?,?,?,?,?,?,?,NULL)",
                      (period, ACCOUNT, POLICY_ID, "accrued", due, accrued, 0))
            for entry in entries:
                c.execute("INSERT INTO payroll_obligations VALUES(:period,:player_id,:covered_from,:covered_to,:monthly_cents,:due_cents,:accrued_cents)", entry)
            if period == "2027-08":
                book_payroll(c, period, due, now)
        if fail_after == "payroll":
            raise RuntimeError("Injected failure after payroll")
        for competition, status in [("Campeonato Carioca", "achieved"), ("Copa do Brasil", "achieved"), ("Copa Sul-Americana", "failed")]:
            c.execute("UPDATE board_objectives SET achieved=? WHERE season=2027 AND competition=?", (status, competition))
        c.execute("UPDATE board_objectives SET objective=? WHERE season=2027 AND competition='Finance'", (
            "Keep transfer commitments <= R$68m (R$55m original + approved R$13m capital); incremental wages <= R$22m/yr; observe restricted category budgets",))
        updates = {
            "saved_state_version": "046C",
            "2027_preseason_status": "Carioca complete; Vasco semifinal exit; 2027 league R01-R25 final and R26-R38 scheduled; continental groups complete",
            "next_fixtures_confirmation": "R26 fully scheduled; next Vasco: 2027-10-03 16:00 Mirassol vs Vasco; unplayed",
            "continental_schedule_note": "046C candidate: overdue unplayed ties rescheduled; calendar_events reserves downstream capacity through 2027-12-31; no results generated",
            "cdb2027": "48 legs complete; all eight R16 ties resolved; four QFs scheduled and downstream slots reserved",
            "brasileirao_calendar_status": "R01-R25 complete (250 matches); R26-R38 scheduled (130); league dates unchanged",
            "saf_2027_budget_status": "Fee authority R$68m; committed R$66.6m, remaining R$1.4m; annual incremental wages R$22m / R$21.66m; reserve R$16m untouched",
            "calendar_2027_repair": "046C candidate calendar reconciliation logged in admin_operations; 12 inherited league rest shortfalls disclosed; no league fixtures moved",
            "sudamericana_knockout_state": "Eight group winners await R16; eight playoffs scheduled on reconciled dates, unplayed; downstream capacity reserved",
            "libertadores_2027_status": "96 group fixtures final; eight R16 ties unplayed with reconciled dates; downstream capacity reserved",
        }
        if revision == "v2":
            updates.update({
                "continental_schedule_note": "046C v2 candidate: known ties rescheduled; undrawn rounds reserve potential qualifiers; all cups finish by 2027-12-21, December 22-January 5 blackout",
                "brasileirao_calendar_status": "R01-R25 complete (250); R26-R38 unplayed (130); 70 controlled kickoff adjustments (36 date, 34 time only); Mirassol-Vasco October 3 16:00 unchanged",
                "calendar_2027_repair": "046C v2 candidate: holidays and return-leg limits enforced, 70 future league kickoff changes individually logged; no new rest violations, one inherited exception retained",
            })
        for key, value in sorted(updates.items()):
            c.execute("UPDATE meta SET value=? WHERE key=?", (value, key))
        for table, key, value in [
            ("cdb_2027_plan_meta", "phase", "quarterfinals_scheduled"),
            ("cdb_2027_plan_meta", "status", "48 legs completed; all R32/R16 ties concluded; QFs unplayed; future calendar reservations in calendar_events"),
            ("libertadores_2027_meta", "schedule_caution", "046C candidate replaces provisional knockout dates; conditional later-round capacity reserved, original results preserved"),
        ]:
            c.execute(f"UPDATE {table} SET value=? WHERE key=?", (value, key))
        operations = diff(before, capture(c, extra))
        for n, op in enumerate(operations, 1):
            c.execute("INSERT INTO admin_operations VALUES(?,?,?,?,?,?,?)", (n, op["operation_id"], op["table"],
                canonical_json(op["key"]), canonical_json(op["before"]) if op["before"] is not None else None,
                canonical_json(op["after"]) if op["after"] is not None else None, op["reason"]))
        if fail_after == "operations":
            raise RuntimeError("Injected failure after operations")
        c.commit()
        return operations
    except BaseException:
        c.rollback()
        raise
