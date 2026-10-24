"""Read-only inspection and audit CLI."""
import argparse
import json
import sqlite3
import sys

from .audit import audit
from .config import database_path
from .db import connect_read_only
from .state import summary


def render_summary(state: dict) -> str:
    v = state["vasco"]
    f = state["next_fixture"]
    lines = [f"THE BRAGA ERA | Save {state['save_version']} | {state['current_date']}",
             f"Vasco: #{v['position']} | {v['points']} pts | {v['played']} played | "
             f"{v['wins']}W {v['draws']}D {v['losses']}L | GF {v['gf']} GA {v['ga']}",
             f"League: {state['league']['clubs']} clubs | {state['league'].get('final', 0)} final | {state['league'].get('scheduled', 0)} scheduled",
             f"Board confidence: {state['board_confidence']}/100 | Braga recorded matches: {state['manager_matches']}"]
    if f:
        lines.append(f"Next: {f['home']} vs {f['away']} | {f['datetime_local']} | {f['round']} | {f['status']}")
    cups = state["competitions"]
    carioca, sula, cdb = (cups[name] for name in ("Carioca", "Sudamericana", "Copa do Brasil"))
    lines.extend([f"Carioca: Vasco {carioca['vasco_status']} in {carioca['vasco_stage']}; {carioca['champion']} champion",
                  f"Sudamericana: Vasco {sula['vasco_status']}, Group {sula['group']} #{sula['position']} ({sula['points']} pts); {sula['group_matches']} group games final",
                  f"Copa do Brasil: Vasco {cdb['vasco_status']} in {cdb['vasco_stage']}; tie winner {cdb['winner']}; {cdb['completed_legs']} completed legs",
                  f"Libertadores: {cups['Libertadores']['group_matches']} group games final",
                  "Overdue unplayed ties: " + "; ".join(f"{k}: {v}" for k, v in state["overdue_ties"].items()),
                  f"Restricted cash: R${state['finance']['restricted_cash_brl']:,.2f} (unreconciled payroll)"])
    for budget in state["finance"]["budgets"]:
        lines.append(f"  {budget['category']}: R${budget['remaining_brl']:,.2f} remaining; {budget['restriction']}")
    lines.extend(["Payroll recorded: " + ", ".join(state["finance"]["payroll_months"]),
                  "August payroll missing; September policy pending. Cash is not acquisition authority.",
                  "Read-only Phase 0. Run audit for historical protections and inherited warnings."])
    return "\n".join(lines)


def main(argv=None) -> int:
    # Windows consoles with older code pages must still report useful errors.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "audit"):
        sub = commands.add_parser(name)
        sub.add_argument("--db", help="SQLite path (overrides BRAGA_ERA_DB and repository default)")
        sub.add_argument("--json", action="store_true", help="Machine-readable output")
        if name == "audit":
            sub.add_argument("--strict", action="store_true", help="Exit 1 for inherited warnings too")
    args = parser.parse_args(argv)
    path = database_path(args.db)
    try:
        with connect_read_only(path) as connection:
            if args.command == "inspect":
                state = summary(connection)
                print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else render_summary(state))
                return 0
            report = audit(connection, path)
            result = report.to_dict()
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for finding in report.findings:
                    print(f"{finding.status} [{finding.code}] {finding.message}")
                print(f"{'PASS' if report.ok else 'FAIL'}: {result['checks']} checks, {result['failures']} failures, {result['warnings']} inherited warnings")
            return 0 if report.ok and not (args.strict and result["warnings"]) else 1
    except (OSError, sqlite3.DatabaseError, KeyError, TypeError, ValueError, StopIteration) as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
