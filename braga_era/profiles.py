"""Explicit validation profiles; a later version never replaces the 046 baseline."""
from importlib.resources import files
import json
from pathlib import Path
import sqlite3

from .audit import AuditReport, _audit_state, _known_issues, audit, schema_records
from .calendar import validate_plan
from .db import connect_read_only, file_sha256
from .history import digest, load_baseline, table_fingerprint
from .migrations import ADDED_TABLES, CHANGED_LEGACY_TABLES, apply
from .payroll import financial_statement


def load_046c_plan():
    return json.loads(files("braga_era").joinpath("profiles/save046c_plan.json").read_text(encoding="utf-8"))


def revision_for(c):
    row=c.execute("SELECT profile FROM checkpoint_info").fetchone()
    if row is None or row[0] not in ("046_to_046C_admin_v1","046_to_046C_admin_v2"):
        raise ValueError("Unsupported administrative candidate profile")
    return "v2" if row[0].endswith("_v2") else "v1"


def authenticate_parent(path: Path):
    path = Path(path).resolve()
    if file_sha256(path) != load_baseline()["database_sha256"]:
        raise ValueError("Parent checksum conflicts with authenticated Save 046")
    with connect_read_only(path) as c:
        report = audit(c, path)
    if not report.ok:
        raise ValueError("Parent does not pass the permanent Save 046 profile")


def expected_046c(parent, plan=None):
    """Reconstruct the authorized delta on an independent in-memory scratch DB."""
    expected = sqlite3.connect(":memory:")
    expected.row_factory = sqlite3.Row
    try:
        parent.backup(expected)
        apply(expected, plan or load_046c_plan(), load_baseline()["database_sha256"])
        return expected
    except BaseException:
        expected.close()
        raise


def audit_046c(c, path: Path, parent_path: Path) -> AuditReport:
    report = AuditReport()
    expected = None
    try:
        authenticate_parent(parent_path)
        report.check("046c.parent", True, "Parent independently passes frozen Save 046 checks and SHA256")
        integrity = [r[0] for r in c.execute("PRAGMA integrity_check")]
        report.check("sqlite.integrity", integrity == ["ok"], str(integrity))
        report.check("sqlite.foreign_keys", not c.execute("PRAGMA foreign_key_check").fetchall(), "Declared foreign keys remain valid")
        with connect_read_only(parent_path) as parent:
            plan = load_046c_plan()
            calendar = validate_plan(parent, plan)
            report.check("046c.calendar_model", calendar["feasible"], "Stage order, fixed league dates, potential qualifiers, rest and workload validated")
            expected = expected_046c(parent, plan)
        baseline = load_baseline()
        actual_tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        report.check("046c.schema", schema_records(c) == schema_records(expected), "Exact authorized migration schema; no unexpected objects")
        report.check("046c.table_inventory", actual_tables == set(baseline["tables"]) | ADDED_TABLES,
                     "Original tables retained; seven explicit administrative tables added")
        if actual_tables != set(baseline["tables"]) | ADDED_TABLES:
            return report
        protected = [t for t in baseline["tables"] if t not in CHANGED_LEGACY_TABLES]
        changed_history = [t for t in protected if table_fingerprint(c, t) != baseline["tables"][t]]
        report.check("046c.historical_records", not changed_history, f"All {len(protected)} protected tables including every fixture, event, player and transfer unchanged; drift: {changed_history}")
        unexpected = [t for t in sorted(actual_tables) if table_fingerprint(c, t) != table_fingerprint(expected, t)]
        report.check("046c.authorized_delta", not unexpected,
                     f"Every table equals independently replayed authorized migration; unexpected: {unexpected}")
        info = dict(c.execute("SELECT * FROM checkpoint_info").fetchone())
        report.check("046c.provenance", info["version"] == "046C" and info["parent_version"] == "046"
                     and info["parent_sha256"] == baseline["database_sha256"] and info["schema_version"] == 1
                     and info["status"] == "candidate" and info["plan_sha256"] == digest(plan),
                     "Version, parent, schema, plan hash and candidate status retained")
        finance = financial_statement(c)
        report.check("046c.finance", finance["restricted_cash_cents"] == 3_055_000_000
                     and finance["accrued_unpaid_cents"] == 155_900_001,
                     "Cash R$30,550,000; accrued unpaid September incremental wages R$1,559,000.01")
        periods = finance["periods"]
        ledger_ids = [p["ledger_id"] for p in periods if p["ledger_id"] is not None]
        report.check("046c.payroll_unique", len({p["period"] for p in periods}) == 9 and len(ledger_ids) == len(set(ledger_ids)) == 8,
                     "Nine unique periods, eight unique cash postings; no September cash debit")
        _audit_state(c, report, version="046C", cash_brl=30_550_000)
        _known_issues(c, report, include_administrative=False)
        report.warning("046c.calendar_exceptions", "12 inherited fixed league turnarounds under 72h retained; added cup/rest reservations comply")
        report.warning("046c.commissioner_calendar", "72h includes travel; extra 6h model infeasible; Christmas semifinals, Dec28/31 finals, long inter-leg gaps and foreign calendars require review")
        report.warning("046c.commissioner_finance", "Actual-day/month-end payroll policy is proposed; untracked base salaries excluded; no canonical promotion")
    except (OSError, sqlite3.DatabaseError, KeyError, TypeError, ValueError, StopIteration) as error:
        report.check("046c.invalid", False, str(error))
    finally:
        if expected is not None:
            expected.close()
    return report


def verify_database(path: Path, version: str, parent_path: Path | None = None):
    if version not in ("046", "046C"):
        raise ValueError(f"Unsupported save profile: {version}; register an explicit future profile before use")
    with connect_read_only(path) as c:
        if version == "046":
            return audit(c, path)
        if parent_path is None:
            raise ValueError("046C validation requires its authenticated parent database")
        if revision_for(c) == "v2":
            from .profile_v2 import audit as audit_v2
            return audit_v2(c,path,parent_path)
        return audit_046c(c, path, parent_path)
