"""Hikari's chronological, spoiler-safe local handoff. No server is required."""

import argparse
import json
from pathlib import Path
from .db import connect_read_only
from .world.storage import writer
from .world.runner import agenda, fixture_preview, narrate


def visible(c):
    done = set()
    for r in c.execute(
        "SELECT e.fixture_key,e.result_json,u.sequence FROM world_executions e LEFT JOIN world_cursors u ON u.fixture_key=e.fixture_key WHERE e.status='applied' ORDER BY e.fixture_key"
    ):
        if r["sequence"] is not None and r["sequence"] == len(
            json.loads(r["result_json"])["events"]
        ):
            done.add(r["fixture_key"])
    return done


def next_group(c):
    shown = visible(c)
    unseen = [
        dict(r)
        for r in c.execute(
            "SELECT f.* FROM world_fixtures f JOIN world_receipts r ON r.fixture_key=f.key ORDER BY kickoff,f.key"
        )
        if r["key"] not in shown
    ]
    if unseen:
        first = unseen[0]["kickoff"]
        return [r for r in unseen if r["kickoff"] == first]
    items = agenda(c)
    return [items[0]] if items else []


def handoff(directory, command, fixture=None, count=1):
    with writer(directory) as (c, policy):
        group = next_group(c)
        keys = {r["key"] for r in group}
        if command == "next":
            return {
                "scope": "NONCANONICAL DEVELOPMENT TEST",
                "events": [
                    {
                        "key": r["key"],
                        "kickoff": r["kickoff"],
                        "kind": r.get("kind", "narration"),
                        "home": r.get("home"),
                        "away": r.get("away"),
                    }
                    for r in group
                ],
                "official_execution_authorized": False,
            }
        if command in ("preview", "narrate"):
            if fixture not in keys:
                raise ValueError(
                    "Complete earlier chronological narration before accessing this fixture"
                )
            if command == "preview":
                return fixture_preview(c, policy, fixture)
        elif command == "table":
            with connect_read_only(Path(directory) / "parent.sqlite") as parent:
                rows = {
                    r["id"]: dict(r)
                    for r in parent.execute(
                        "SELECT c.id,c.name,c.points,c.played,c.wins,c.draws,c.losses,c.gf,c.ga FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027"
                    )
                }
            shown = visible(c)
            for f in c.execute(
                "SELECT * FROM world_fixtures WHERE competition='LEAGUE' AND status='final' ORDER BY kickoff,key"
            ):
                if f["key"] not in shown:
                    continue
                h, a = int(f["home"][5:]), int(f["away"][5:])
                for own, gf, ga in (
                    (h, f["home_goals"], f["away_goals"]),
                    (a, f["away_goals"], f["home_goals"]),
                ):
                    r = rows[own]
                    r["played"] += 1
                    r["gf"] += gf
                    r["ga"] += ga
                    r["wins"] += int(gf > ga)
                    r["draws"] += int(gf == ga)
                    r["losses"] += int(gf < ga)
                    r["points"] += 3 if gf > ga else int(gf == ga)
            return {
                "scope": "NONCANONICAL DEVELOPMENT TEST",
                "basis": "accepted parent plus narrated final whistles only",
                "standings": sorted(
                    rows.values(),
                    key=lambda r: (
                        -r["points"],
                        -r["wins"],
                        -(r["gf"] - r["ga"]),
                        -r["gf"],
                        r["name"],
                    ),
                ),
            }
        elif command == "finances":
            # Do not expose later obligations just because a diagnostic season was simulated.
            with connect_read_only(Path(directory) / "parent.sqlite") as parent:
                budgets = [
                    dict(r)
                    for r in parent.execute("SELECT * FROM finance_budget ORDER BY id")
                ]
                ledger = [
                    dict(r)
                    for r in parent.execute("SELECT * FROM finance_ledger ORDER BY id")
                ]
            horizon = min(
                (r["kickoff"] for r in group),
                default=c.execute("SELECT clock FROM world_info").fetchone()[0],
            )
            obligations = [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM world_obligations WHERE status='paid' AND kickoff<? ORDER BY kickoff",
                    (horizon,),
                )
            ]
            return {
                "scope": "NONCANONICAL DEVELOPMENT TEST",
                "accepted_budgets": budgets,
                "accepted_ledger": ledger,
                "revealed_forward_obligations": obligations,
            }
        elif command != "narrate":
            raise ValueError("Unknown gameplay command")
    return narrate(directory, fixture, count)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory")
    p.add_argument(
        "command", choices=("next", "preview", "narrate", "table", "finances")
    )
    p.add_argument("--fixture")
    p.add_argument("--count", type=int, default=1)
    a = p.parse_args()
    print(
        json.dumps(
            handoff(a.directory, a.command, a.fixture, a.count),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
