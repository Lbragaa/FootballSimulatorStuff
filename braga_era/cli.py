"""Read-only inspection, audited checkpoints and noncanonical match sandboxes."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
import zipfile

from .config import database_path
from .db import connect_read_only
from .state import summary
from .profiles import verify_database
from .checkpoints import (
    create_candidate,
    export_checkpoint,
    export_parent,
    restore_checkpoint,
    verify_archive,
    verify_checkpoint,
)


def render_summary(state: dict) -> str:
    v = state["vasco"]
    f = state["next_fixture"]
    lines = [
        f"THE BRAGA ERA | Save {state['save_version']} | {state['current_date']}",
        f"Vasco: #{v['position']} | {v['points']} pts | {v['played']} played | "
        f"{v['wins']}W {v['draws']}D {v['losses']}L | GF {v['gf']} GA {v['ga']}",
        f"League: {state['league']['clubs']} clubs | {state['league'].get('final', 0)} final | {state['league'].get('scheduled', 0)} scheduled",
        f"Board confidence: {state['board_confidence']}/100 | Braga recorded matches: {state['manager_matches']}",
    ]
    if f:
        lines.append(
            f"Next: {f['home']} vs {f['away']} | {f['datetime_local']} | {f['round']} | {f['status']}"
        )
    cups = state["competitions"]
    carioca, sula, cdb = (
        cups[name] for name in ("Carioca", "Sudamericana", "Copa do Brasil")
    )
    lines.extend(
        [
            f"Carioca: Vasco {carioca['vasco_status']} in {carioca['vasco_stage']}; {carioca['champion']} champion",
            f"Sudamericana: Vasco {sula['vasco_status']}, Group {sula['group']} #{sula['position']} ({sula['points']} pts); {sula['group_matches']} group games final",
            f"Copa do Brasil: Vasco {cdb['vasco_status']} in {cdb['vasco_stage']}; tie winner {cdb['winner']}; {cdb['completed_legs']} completed legs",
            f"Libertadores: {cups['Libertadores']['group_matches']} group games final",
            "Overdue unplayed ties: "
            + "; ".join(f"{k}: {v}" for k, v in state["overdue_ties"].items()),
            f"Restricted cash: R${state['finance']['restricted_cash_brl']:,.2f} (unreconciled payroll)",
        ]
    )
    for budget in state["finance"]["budgets"]:
        lines.append(
            f"  {budget['category']}: R${budget['remaining_brl']:,.2f} remaining; {budget['restriction']}"
        )
    lines.extend(
        [
            "Payroll recorded: " + ", ".join(state["finance"]["payroll_months"]),
            "Cash is not acquisition authority.",
        ]
    )
    if "payroll" in state:
        label = (
            "Accepted administrative checkpoint (Task 03A); official matches not authorized"
            if state.get("acceptance")
            else "Unaccepted candidate"
        )
        lines.extend(
            [
                f"Checkpoint: {label}; immutable package status: {state['checkpoint']['status']}",
                f"Accrued unpaid incremental wages: R${state['payroll']['accrued_unpaid_cents']/100:,.2f}; September cash not yet due",
            ]
        )
    else:
        lines.append("August payroll missing; September policy pending.")
    lines.append(
        "Read-only inspection. Run audit with the appropriate save profile for historical protections and warnings."
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    # Windows consoles with older code pages must still report useful errors.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "audit"):
        sub = commands.add_parser(name)
        sub.add_argument(
            "--db", help="SQLite path (overrides BRAGA_ERA_DB and repository default)"
        )
        sub.add_argument("--json", action="store_true", help="Machine-readable output")
        if name == "audit":
            sub.add_argument(
                "--strict",
                action="store_true",
                help="Exit 1 for inherited warnings too",
            )
            sub.add_argument(
                "--profile",
                choices=["046", "046C"],
                help="Default: select the strict profile for the recorded save version",
            )
            sub.add_argument(
                "--parent",
                type=Path,
                help="Authenticated parent DB required by 046C profile",
            )
    save = commands.add_parser(
        "save",
        help="Create candidates, verify, export or restore; no promotion command",
    )
    save_commands = save.add_subparsers(dest="save_command", required=True)
    create = save_commands.add_parser("create")
    create.add_argument(
        "--parent",
        type=Path,
        help="Default: original frozen 046 parent, not the accepted administrative checkpoint",
    )
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--version", default="046C")
    create.add_argument(
        "--revision",
        choices=["v1", "v2"],
        default="v2",
        help="v1 is rejected and retained only for archival reproduction",
    )
    verify = save_commands.add_parser("verify")
    verify.add_argument("source", type=Path, help="Checkpoint directory or ZIP")
    export = save_commands.add_parser("export")
    export.add_argument(
        "source", type=Path, help="Verified checkpoint directory or original 046 DB"
    )
    export.add_argument("--output", type=Path, required=True)
    restore = save_commands.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--output", type=Path, required=True)
    cal = commands.add_parser(
        "calendar", help="Read-only deterministic feasibility proposal"
    )
    cal.add_argument("--db")
    cal.add_argument("--strategy", choices=["A", "B", "C", "compare"], default="B")
    cal.add_argument("--minimum-rest-hours", type=int, default=72)
    cal.add_argument("--travel-buffer-hours", type=int, default=0)
    cal.add_argument("--deadline")
    cal.add_argument("--maximum-leg-interval-days", type=int, default=14)
    cal.add_argument("--blackout-start", default="12-22")
    cal.add_argument("--blackout-end", default="01-05")
    sandbox = commands.add_parser(
        "sandbox", help="Disposable, NONCANONICAL match only; no official persistence"
    )
    sandbox.add_argument("--db")
    sandbox.add_argument("--output", type=Path, required=True)
    sandbox.add_argument(
        "--seed",
        required=True,
        help="Commit this seed before any lineup or match draws",
    )
    selection = sandbox.add_mutually_exclusive_group()
    selection.add_argument(
        "--fixture",
        help="league:ID or calendar:EVENT_ID; default earliest non-Vasco league fixture with recorded squads",
    )
    selection.add_argument(
        "--synthetic",
        action="store_true",
        help="Hypothetical Vasco–Fluminense using current recorded squads",
    )
    narrate = commands.add_parser(
        "narrate",
        help="Consume the next ordered sandbox events; postmatch sealed until the whistle",
    )
    narrate.add_argument("directory", type=Path)
    narrate.add_argument("--count", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.command == "narrate":
            from .engine.sandbox import next_narration

            print(
                json.dumps(
                    next_narration(args.directory, args.count),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "save":
            if args.save_command == "create":
                parent = (
                    args.parent
                    or Path(__file__).resolve().parents[1]
                    / "data/handoff/canonical/braga_save.sqlite"
                )
                result = create_candidate(
                    parent, args.output, version=args.version, revision=args.revision
                )
            elif args.save_command == "verify":
                result = (
                    verify_checkpoint(args.source)
                    if args.source.is_dir()
                    else verify_archive(args.source)
                )
            elif args.save_command == "export":
                result = (
                    export_checkpoint(args.source, args.output)
                    if args.source.is_dir()
                    else export_parent(args.source, args.output)
                )
            else:
                result = restore_checkpoint(args.archive, args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        path = database_path(args.db)
        if args.command == "sandbox":
            from .engine.sandbox import run

            print(
                json.dumps(
                    run(path, args.output, args.seed, args.fixture, args.synthetic),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "calendar":
            from .calendar_v2 import (
                Policy,
                propose as propose_v2,
                validate as validate_v2,
                explore,
            )

            with connect_read_only(path) as connection:
                if args.strategy == "compare":
                    if (
                        args.deadline
                        or args.minimum_rest_hours != 72
                        or args.travel_buffer_hours
                        or args.maximum_leg_interval_days != 14
                        or args.blackout_start != "12-22"
                        or args.blackout_end != "01-05"
                    ):
                        raise ValueError(
                            "Comparison uses disclosed fixed presets; choose an individual strategy for custom constraints"
                        )
                    result = explore(connection)
                else:
                    policy = Policy(
                        minimum_rest_hours=args.minimum_rest_hours,
                        international_buffer_hours=args.travel_buffer_hours,
                        deadline=args.deadline
                        or (
                            "2028-01-15 22:00"
                            if args.strategy == "C"
                            else "2027-12-21 22:00"
                        ),
                        maximum_leg_interval_days=args.maximum_leg_interval_days,
                        blackout_start_month_day=args.blackout_start,
                        blackout_end_month_day=args.blackout_end,
                    )
                    plan = propose_v2(connection, args.strategy, policy)
                    result = {
                        "plan": plan,
                        "feasibility": validate_v2(connection, plan),
                    }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return (
                0
                if result.get("recommendation")
                or result.get("feasibility", {}).get("feasible")
                else 1
            )
        if args.command == "audit":
            with connect_read_only(path) as connection:
                version = connection.execute(
                    "SELECT value FROM meta WHERE key='saved_state_version'"
                ).fetchone()[0]
            profile = args.profile or version
            parent = args.parent or (
                path.parent / "parent.sqlite" if profile == "046C" else None
            )
            report = verify_database(path, profile, parent)
            result = report.to_dict()
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for finding in report.findings:
                    print(f"{finding.status} [{finding.code}] {finding.message}")
                print(
                    f"{'PASS' if report.ok else 'FAIL'}: {result['checks']} checks, {result['failures']} failures, {result['warnings']} warnings"
                )
            return 0 if report.ok and not (args.strict and result["warnings"]) else 1
        with connect_read_only(path) as connection:
            if args.command == "inspect":
                state = summary(connection)
                from .acceptance import accepted_context

                if context := accepted_context(path):
                    state["acceptance"] = context
                print(
                    json.dumps(state, ensure_ascii=False, indent=2)
                    if args.json
                    else render_summary(state)
                )
                return 0
    except (
        OSError,
        sqlite3.DatabaseError,
        KeyError,
        TypeError,
        ValueError,
        StopIteration,
        NotImplementedError,
        zipfile.BadZipFile,
    ) as error:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
