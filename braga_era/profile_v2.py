"""Revised 046C profile. The rejected v1 artifact remains independently verifiable."""
from importlib.resources import files
import json
from pathlib import Path
import sqlite3

from .audit import AuditReport, _audit_state, _known_issues, schema_records
from .calendar_v2 import validate, realism_score
from .db import connect_read_only
from .history import completed_fixtures, digest, load_baseline, table_fingerprint
from .migrations import ADDED_TABLES, CHANGED_LEGACY_TABLES, apply
from .payroll import financial_statement, obligations

PROFILE = "046_to_046C_admin_v2"
APPROVALS = ["controlled_70_future_kickoffs_36_date_changes_pin_mirassol_vasco",
             "72h_turnaround_including_travel_one_inherited_exception_foreign_calendar_limits",
             "accept_candidate_hash_and_provisionally_supported_payroll_policy"]


def load_plan():
    return json.loads(files("braga_era").joinpath("profiles/save046c_plan_v2.json").read_text(encoding="utf-8"))


def expected(parent):
    scratch=sqlite3.connect(":memory:")
    scratch.row_factory=sqlite3.Row
    try:
        parent.backup(scratch)
        apply(scratch,load_plan(),load_baseline()["database_sha256"],revision="v2")
        return scratch
    except BaseException:
        scratch.close()
        raise


def audit(c, path: Path, parent_path: Path):
    from .profiles import authenticate_parent
    report=AuditReport()
    scratch=None
    try:
        authenticate_parent(parent_path)
        report.check("v2.parent",True,"Original Save 046 and permanent baseline authenticated independently")
        report.check("sqlite.integrity",[r[0] for r in c.execute("PRAGMA integrity_check")]==["ok"],"SQLite integrity")
        report.check("sqlite.foreign_keys",not c.execute("PRAGMA foreign_key_check").fetchall(),"Declared foreign keys")
        plan=load_plan()
        with connect_read_only(parent_path) as parent:
            calendar=validate(parent,plan)
            scratch=expected(parent)
        report.check("v2.calendar",calendar["feasible"],"Holiday blackout, bounded legs, confirmed pairings, conditional reservations, rest/workload and league order checked")
        baseline=load_baseline()
        names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        report.check("v2.schema",schema_records(c)==schema_records(scratch),"Exact explicit administrative schema")
        report.check("v2.table_inventory",names==set(baseline["tables"])|ADDED_TABLES,"Original tables retained and seven administrative tables added")
        if names!=set(baseline["tables"])|ADDED_TABLES:
            return report
        protected=set(baseline["tables"])-CHANGED_LEGACY_TABLES-{"fixtures"}
        drift=[t for t in sorted(protected) if table_fingerprint(c,t)!=baseline["tables"][t]]
        report.check("v2.historical_tables",not drift,f"All {len(protected)} untouched original tables preserved, including players/attribution/events/transfers; drift: {drift}")
        report.check("v2.completed_fixtures",digest(completed_fixtures(c))==baseline["completed_fixtures_sha256"],"All 331 completed fixture rows unchanged in every column")
        differences=[t for t in sorted(names) if table_fingerprint(c,t)!=table_fingerprint(scratch,t)]
        report.check("v2.authorized_delta",not differences,f"Every table equals independent replay, including exact permitted scheduled kickoff changes; drift: {differences}")
        info=dict(c.execute("SELECT * FROM checkpoint_info").fetchone())
        report.check("v2.provenance",info["profile"]==PROFILE and info["version"]=="046C" and info["parent_sha256"]==baseline["database_sha256"]
                     and info["plan_sha256"]==digest(plan) and info["status"]=="candidate","Version, v2 revision, parent, plan and unaccepted status")
        finance=financial_statement(c)
        report.check("v2.finance",finance["restricted_cash_cents"]==3_055_000_000 and finance["accrued_unpaid_cents"]==155_900_001,
                     "August R$1.38m settled once; cash R$30.55m; September liability R$1,559,000.01, no September cash")
        player_rows=[dict(r) for r in c.execute("SELECT * FROM payroll_obligations WHERE period='2027-09' ORDER BY player_id")]
        derived=obligations(c,"2027-09","2027-09-26 23:30")
        report.check("v2.player_payroll",player_rows==derived and sum(r["due_cents"] for r in derived)==179_966_667
                     and sum(r["accrued_cents"] for r in derived)==155_900_001,
                     "September due/accrued obligations reconcile per player under actual-day and per-player cent rounding")
        periods=finance['periods']
        ids=[p['ledger_id'] for p in periods if p['ledger_id'] is not None]
        report.check("v2.periods",len(periods)==9 and len(ids)==len(set(ids))==8,"Nine unique obligation periods; eight unique cash ledger links")
        report.check("v2.holidays",calendar['holiday_conflicts']==0,"No new or moved match during December 22-January 5")
        report.check("v2.rest",not calendar['new_rest_shortfalls'] and calendar['minimum_new_turnaround_hours']>=72,
                     "No newly introduced sub-72h interval; inherited exceptions identified by exact original pair and kickoffs")
        _audit_state(c,report,version="046C",cash_brl=30_550_000)
        _known_issues(c,report,include_administrative=False)
        report.warning("v2.calendar_review",f"70 future kickoffs change (36 matchdays, 34 time only); Mirassol-Vasco pinned; {len(calendar['inherited_league_rest_exceptions'])} inherited league exception remains")
        report.warning("v2.travel_scope","72h is kickoff-to-kickoff including travel; six extra hours are a sensitivity scenario, not hidden relaxation; foreign schedules/itineraries remain unknown")
        report.warning("v2.acceptance","Payroll direction provisionally supported for candidate preparation; full candidate acceptance and R26 require subsequent authorization")
    except (OSError,sqlite3.DatabaseError,KeyError,TypeError,ValueError,StopIteration) as error:
        report.check("v2.invalid",False,str(error))
    finally:
        if scratch is not None:
            scratch.close()
    return report


def report(metadata,validation,calendar,finance,operations):
    plan=load_plan()
    score=realism_score(calendar)
    lines=["# Revised Save 046C — proposal v2, not accepted", "",
        f"Fictional date remains {metadata['fictional_date']}. No matches simulated, no R26, no canonical promotion.",
        f"Database SHA256: `{metadata['database_sha256']}`. Parent: `{metadata['parent_sha256']}`.",
        "Original holiday proposal v1 is preserved separately and explicitly rejected by Task 02B.","",
        "## Recommended strategy B: controlled league adjustment", "",
        "All cups finish in 2027; December 22–January 5 is a hard blackout. Mirassol–Vasco on October 3 at 16:00 is unchanged.",
        f"70 scheduled kickoffs change: 36 calendar dates and 34 times only. No completed fixture changes. Comparison heuristic score: {score['total']}/100.",
        f"Return legs span at most {calendar['maximum_leg_interval_days']:.2f} days; minimum new kickoff turnaround {calendar['minimum_new_turnaround_hours']:.0f}h. Maximum workload {calendar['maximum_matches_in_rolling_window']} in eight days.",
        f"One inherited rest exception remains; no new shortfalls. Maximum interstage wait: {calendar['maximum_stage_wait_days']:.1f} days. These are conservative potential-qualifier reservations, not assumed winners.","",
        "| Known tie or provisional reservation | Leg | Original date | Proposed kickoff | Entry type |", "|---|---:|---|---|---|"]
    for e in sorted(plan['events'],key=lambda e:(e['kickoff'],e['event_id'])):
        lines.append(f"| {e['event_id']} | {e['leg']} | {e['previous_date'] or 'undrawn'} | {e['kickoff']} | {'known fixture' if e['home'] and e['away'] else 'provisional reservation'} |")
    lines += ["", "## Every league kickoff adjustment", "", "| Fixture ID | Original kickoff | Proposed kickoff |", "|---:|---|---|"]
    lines += [f"| {m['fixture_id']} | {m['before']} | {m['after']} |" for m in plan['league_adjustments']]
    lines += ["", "Vasco changes only: Fluminense–Vasco R28, October 17 → October 18 at 16:00; Athletico-PR–Vasco R38, December 19 → December 18 at 16:00. R26 Mirassol–Vasco is pinned.",
        "", "## Finance and board evidence", "",
        "August: R$1,380,000 paid once. Restricted cash: R$31,930,000 → R$30,550,000. September cash: zero; accrued liability R$1,559,000.01; full-month obligation R$1,799,666.67. Actual-day proration and per-player cent rounding apply. No untracked base payroll, new capital or duplicate annual commitment debit.",
        "Annual incremental commitments R$21.66m; wage headroom R$0.34m; fee authority remaining R$1.4m; agents/scouting remaining R$2.19m; restricted emergency reserve R$16m unchanged.","",
        "| Player ID | Monthly BRL | September due BRL | Accrued through Sep26 BRL |", "|---:|---:|---:|---:|"]
    # Per-player report derived from the same contracts and independently audited amounts.
    for row in finance['player_obligations']:
        if row['period']=='2027-09':
            lines.append(f"| {row['player_id']} | {row['monthly_cents']/100:,.2f} | {row['due_cents']/100:,.2f} | {row['accrued_cents']/100:,.2f} |")
    lines += ["", "Carioca/Copa do Brasil objectives achieved; Sudamericana failed. League/youth/season-wide Finance stay pending. R$68m fee wording retained.",
        "", "## Remaining commissioner decisions", "",
        "Accept or revise the complete 70-kickoff inventory, the 72h total-turnaround/travel scope and the one preserved original shortfall. Finance direction is supported for preparing this candidate, not automatic promotion. No 2028 extension is needed for the recommendation; the scored alternative requires separate postseason, registration/contracts, preseason and finance policy decisions.",
        "Unknown foreign domestic commitments and actual routes/venues prevent a global-calendar guarantee. No rest rule is weakened below 72h; any stronger travel-plus-recovery requirement needs a new solve. Scores are transparent planning heuristics, not calibrated sport probabilities.",
        "", f"Operations: {len(operations)} logged keyed changes; complete changes.json includes those log rows too. Changed tables: {', '.join(metadata['changed_tables'])}.",
        "", "## Validation", "",f"{validation['checks']} checks, {validation['failures']} failures, {validation['warnings']} warnings."]
    lines += [f"- {f['status']} [{f['code']}]: {f['message']}" for f in validation['findings']]
    return '\n'.join(lines)+'\n'
