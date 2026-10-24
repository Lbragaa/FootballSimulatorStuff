"""Reusable Save 046 audits. Known inherited defects remain visible warnings."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
import sqlite3

from .db import file_sha256
from .history import completed_fixtures, digest, load_baseline, table_fingerprint
from .state import ACCOUNT, LEAGUE, standings


@dataclass(frozen=True)
class Finding:
    code: str
    status: str
    message: str


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def check(self, code: str, condition: bool, message: str) -> None:
        self.findings.append(Finding(code, "PASS" if condition else "FAIL", message))

    def warning(self, code: str, message: str) -> None:
        self.findings.append(Finding(code, "WARN", message))

    @property
    def ok(self) -> bool:
        return not any(f.status == "FAIL" for f in self.findings)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checks": sum(f.status != "WARN" for f in self.findings),
                "failures": sum(f.status == "FAIL" for f in self.findings),
                "warnings": sum(f.status == "WARN" for f in self.findings),
                "findings": [asdict(f) for f in self.findings]}


def schema_records(connection) -> list[list]:
    return [list(r) for r in connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]


def _audit_state(c, report: AuditReport, *, version="046", cash_brl=31_930_000) -> None:
    meta = dict(c.execute("SELECT key,value FROM meta"))
    expected_meta = {"saved_state_version": version, "current_date": "2027-09-26 23:30",
                     "next_match_fixture": "2027-10-03 Mirassol vs Vasco, Brasileirão R26",
                     "board_confidence": "61", "braga_matches": "45"}
    report.check(f"save{version.lower()}.meta", all(meta.get(k) == v for k, v in expected_meta.items()),
                 f"Save {version} date, next fixture, confidence and manager counter match")
    table = standings(c)
    participants = {r["id"] for r in table}
    report.check("league.participants", len(participants) == 20, "20 distinct 2027 league clubs")
    fixtures = [dict(r) for r in c.execute("SELECT * FROM fixtures WHERE competition=? ORDER BY id", (LEAGUE,))]
    report.check("league.inventory", len(fixtures) == 380 and
                 sum(f["status"] == "final" for f in fixtures) == 250 and
                 sum(f["status"] == "scheduled" for f in fixtures) == 130,
                 "380 league fixtures: 250 final, 130 scheduled")
    valid_rounds = True
    for number in range(1, 39):
        group = [f for f in fixtures if f["round"] == f"R{number:02}"]
        clubs = [t for f in group for t in (f["home_id"], f["away_id"])]
        valid_rounds &= (len(group) == 10 and len(set(clubs)) == 20 and set(clubs) == participants
                         and all(f["status"] == ("final" if number <= 25 else "scheduled") for f in group))
    report.check("league.rounds", valid_rounds, "38 ten-game rounds; each club appears once per round")
    pairings = [(f["home_id"], f["away_id"]) for f in fixtures]
    report.check("league.pairings", len(set(pairings)) == 380 and all(h != a for h, a in pairings),
                 "Every ordered home-away pairing occurs once")
    report.check("league.future_unplayed", all(f["home_goals"] is None and f["away_goals"] is None
                 for f in fixtures if f["status"] == "scheduled"), "Scheduled league matches have no scores")
    discrepancies = []
    for team in table:
        w = d = lost = gf = ga = played = 0
        for f in fixtures:
            if f["status"] != "final" or team["id"] not in (f["home_id"], f["away_id"]):
                continue
            home = f["home_id"] == team["id"]
            g, conceded = (f["home_goals"], f["away_goals"]) if home else (f["away_goals"], f["home_goals"])
            if not isinstance(g, int) or not isinstance(conceded, int) or min(g, conceded) < 0:
                discrepancies.append(f"invalid score {f['id']}")
                continue
            played += 1
            gf += g
            ga += conceded
            w += g > conceded
            d += g == conceded
            lost += g < conceded
        if (played, w, d, lost, gf, ga, 3*w+d) != tuple(team[k] for k in
                ("played", "wins", "draws", "losses", "gf", "ga", "points")):
            discrepancies.append(team["name"])
    report.check("league.standings", not discrepancies, "All 20 standings recomputed from results" +
                 (f"; discrepancies: {discrepancies}" if discrepancies else ""))
    vasco = next((r for r in table if r["name"] == "Vasco"), {})
    report.check("vasco.standings", tuple(vasco.get(k) for k in
                 ("position", "points", "played", "wins", "draws", "losses", "gf", "ga")) ==
                 (9, 38, 25, 11, 5, 9, 36, 37), "Vasco ninth: 38 pts, 25 played, 11W 5D 9L, 36-37")
    final = c.execute("""SELECT f.* FROM fixtures f JOIN clubs h ON h.id=f.home_id
        JOIN clubs a ON a.id=f.away_id WHERE f.competition=? AND f.round='R25'
        AND h.name='Vasco' AND a.name='Palmeiras'""", (LEAGUE,)).fetchall()
    report.check("vasco.palmeiras", len(final) == 1 and final[0]["status"] == "final" and
                 (final[0]["home_goals"], final[0]["away_goals"]) == (3, 2), "Vasco 3-2 Palmeiras is final, once")
    next_game = c.execute("""SELECT f.* FROM fixtures f JOIN clubs h ON h.id=f.home_id
        JOIN clubs a ON a.id=f.away_id WHERE f.competition=? AND f.round='R26'
        AND h.name='Mirassol' AND a.name='Vasco'""", (LEAGUE,)).fetchall()
    report.check("vasco.next", len(next_game) == 1 and next_game[0]["status"] == "scheduled" and
                 next_game[0]["datetime_local"] == "2027-10-03 16:00" and
                 next_game[0]["home_goals"] is None and next_game[0]["away_goals"] is None,
                 "Mirassol-Vasco, October 3 at 16:00, R26 remains unplayed")
    # R25 has complete event, shot and appearance records. Check each side,
    # not just aggregate goals (which could hide attribution errors).
    event_errors = []
    for f in fixtures:
        if f["round"] != "R25":
            continue
        for side in ("home", "away"):
            tid = f[f"{side}_id"]
            args = (f["id"], tid)
            goals = c.execute("SELECT count(*) FROM events WHERE fixture_id=? AND club_id=? AND event_type='GOAL'", args).fetchone()[0]
            shots = c.execute("SELECT coalesce(sum(goal),0),count(*),coalesce(sum(on_target),0),coalesce(sum(xg),0) FROM shots WHERE fixture_id=? AND club_id=?", args).fetchone()
            appearances = c.execute("SELECT coalesce(sum(goals),0),sum(starter=1),count(distinct player_id),count(*) FROM player_matches WHERE fixture_id=? AND club_id=?", args).fetchone()
            if (goals, shots[0], appearances[0]) != (f[f"{side}_goals"],)*3 or appearances[1] != 11 or appearances[2] != appearances[3] or (
                    shots[1], shots[2], round(shots[3], 2)) != (f[f"{side}_shots"], f[f"{side}_sot"], f[f"{side}_xg"]):
                event_errors.append(args)
    report.check("r25.events", not event_errors, f"R25 goals, shots, xG and 22 starters reconcile; mismatches: {event_errors}")
    rojas = list(c.execute("""SELECT minute,event_type FROM events WHERE fixture_id=322 AND player_id=32
        ORDER BY minute,id"""))
    report.check("r25.rojas_order", [tuple(r) for r in rojas] == [(82, "SUBSTITUTION"), (82, "GOAL")],
                 "Johan Rojas enters before his 82nd-minute winner in database event order")
    identity = c.execute("SELECT canonical_id FROM player_identity_resolution WHERE archived_id=196").fetchone()
    players = {r["id"]: dict(r) for r in c.execute("SELECT * FROM players WHERE id IN (196,354)")}
    report.check("players.identities", identity is not None and identity[0] == 354 and
                 "historical Botafogo archive" in players.get(196, {}).get("name", "") and
                 players.get(354, {}).get("name") == "Jefferson Savarino",
                 "Archived Savarino #196 and active #354 retained as separate identities")
    for label, query, expected in [
        ("players", "SELECT count(*) FROM players", 547),
        ("transfers", "SELECT count(*) FROM transfers", 9),
        ("archive2026", "SELECT count(*) FROM league_standings_archive WHERE season=2026", 20),
        ("libertadores.groups", "SELECT count(*) FROM libertadores_2027_fixtures WHERE status='final'", 96),
        ("sudamericana.groups", "SELECT count(*) FROM sudamericana_2027_fixtures WHERE status='final'", 96),
        ("cdb.legs", "SELECT count(*) FROM cdb_2027_legs", 48),
    ]:
        report.check(f"inventory.{label}", c.execute(query).fetchone()[0] == expected, f"{label}: {expected} records")
    cash = c.execute("SELECT sum(amount_brl) FROM finance_ledger WHERE account=?", (ACCOUNT,)).fetchone()[0]
    report.check("finance.cash", cash == cash_brl, f"Restricted ledger cash R${cash_brl:,.0f}")
    budgets = {r[0]: r[1] for r in c.execute("SELECT category,amount_brl-spent_brl FROM finance_budget WHERE season=2027")}
    report.check("finance.authority", all(budgets.get(k) == v for k, v in {
        "Transfer fees": 1_400_000, "Incremental wages": 340_000,
        "Scouting and agents": 2_190_000, "Emergency reserve": 16_000_000}.items()),
        "Acquisition, annual wage, agent headroom and reserved funds match approved budgets")


def _known_issues(c, report: AuditReport, *, include_administrative=True) -> None:
    now = c.execute("SELECT value FROM meta WHERE key='current_date'").fetchone()[0][:10]
    overdue = []
    for table, date, extra in [("libertadores_2027_round_of_16", "second_leg_date", ""),
                               ("sudamericana_2027_playoffs", "second_leg_date", ""),
                               ("cdb_2027_bracket", "leg2_date", "AND stage='Quartas'")]:
        count = c.execute(f"SELECT count(*) FROM {table} WHERE status='scheduled' AND {date}<? {extra}", (now,)).fetchone()[0]
        overdue.append(count)
    if include_administrative:
        report.warning("known.calendar", f"Overdue unplayed ties: Libertadores {overdue[0]}, Sudamericana {overdue[1]}, Copa do Brasil QF {overdue[2]}; no scores invented")
    months = [r[0] for r in c.execute("SELECT substr(dated,1,7) FROM finance_ledger WHERE category='incremental wage payroll' ORDER BY dated")]
    if include_administrative:
        report.warning("known.payroll", f"Recorded payroll periods: {', '.join(months)}. August absent; September policy pending; cash is unreconciled")
    pending = c.execute("SELECT count(*) FROM board_objectives WHERE achieved='pending'").fetchone()[0]
    if include_administrative:
        report.warning("known.objectives", f"{pending} board objective flags pending, including settled cup outcomes; finance wording still names original R$55m fee cap")
    report.warning("known.2026", "2026 final standings archived, granular fixtures partial (71 league records); do not reconstruct missing results")
    missing = c.execute("SELECT count(*) FROM fixtures WHERE status='final' AND (datetime_local IS NULL OR datetime_local NOT LIKE '____-__-__%')").fetchone()[0]
    report.warning("known.dates", f"{missing} completed fixtures lack an ISO calendar date; preserve unknowns")
    cards = c.execute("""SELECT count(*) FROM events e JOIN player_matches pm ON pm.fixture_id=e.fixture_id
        AND pm.player_id=e.player_id WHERE e.event_type IN ('YELLOW','RED') AND pm.starter=1 AND e.minute>pm.minutes""").fetchone()[0]
    report.warning("known.cards", f"{cards} historical cards occur after the starter's recorded exit minute; no retrospective event edits")
    empty = c.execute("SELECT count(*) FROM match_engine_audit WHERE coalesce(home_prematch_xg,0)=0 AND coalesce(away_prematch_xg,0)=0").fetchone()[0]
    report.warning("known.engine_metrics", f"{empty} engine-audit rows have both prematch xG fields empty/zero; historical reproducibility limited")
    report.warning("known.identity", "Savarino #196 archive and active #354 both currently reference Fluminense club_id=5; use identity resolution for eligibility")
    report.warning("known.legacy_code", "Reference engine and episode scripts contain top-level writes, absolute paths, text replacement and exec; inspected only, never imported or executed")
    report.warning("known.json_order", "results046.json sorts Rojas GOAL before SUBSTITUTION at minute 82; database IDs and episode correctly place substitution first")


def audit(connection, path: Path) -> AuditReport:
    """Validate this fixed checkpoint; intentionally rejects later saves or copies with edits."""
    report = AuditReport()
    baseline = load_baseline()
    try:
        integrity = [r[0] for r in connection.execute("PRAGMA integrity_check")]
        report.check("sqlite.integrity", integrity == ["ok"], f"SQLite integrity: {integrity}")
        if integrity != ["ok"]:
            return report
        report.check("sqlite.foreign_keys", not connection.execute("PRAGMA foreign_key_check").fetchall(), "Declared foreign keys have no violations")
        schema = schema_records(connection)
        report.check("history.schema", digest(schema) == baseline["schema_sha256"], "Schema matches original Save 046")
        actual_names = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if actual_names != set(baseline["tables"]):
            report.check("history.tables", False, "Missing or unexpected user tables; cannot safely inspect this schema")
            return report
        report.check("history.database_sha256", file_sha256(path) == baseline["database_sha256"], "Database bytes match canonical Save 046 SHA256")
        report.check("history.completed_fixtures", digest(completed_fixtures(connection)) == baseline["completed_fixtures_sha256"],
                     "All 331 completed fixtures in the main fixture table match the historical snapshot")
        changed = [name for name, expected in baseline["tables"].items()
                   if table_fingerprint(connection, name) != expected]
        report.check("history.all_tables", not changed, "All 64 user-table logical hashes match" + (f"; changed: {', '.join(changed)}" if changed else ""))
        _audit_state(connection, report)
        _known_issues(connection, report)
    except (sqlite3.DatabaseError, KeyError, TypeError, ValueError, StopIteration) as error:
        report.check("audit.invalid_data", False, f"Cannot validate checkpoint: {error}")
    return report
