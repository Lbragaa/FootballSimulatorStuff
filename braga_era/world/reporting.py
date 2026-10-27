"""Spoiler-safe engineering summaries and explicitly private full-world diagnostics."""

from dataclasses import asdict
import json
from pathlib import Path
from ..checkpoints import write_json
from ..db import connect_read_only, file_sha256
from ..history import digest
from .storage import writer, logical_hash
from .runner import fixture_preview, advance
from .adapters import adapter
from .rosters import distribution
from .audit import audit
from . import SCOPE


def preflight(c, policy):
    fixtures = c.execute(
        "SELECT * FROM world_fixtures WHERE kickoff LIKE '2027-09-30%' ORDER BY key"
    ).fetchall()
    out = []
    for f in fixtures:
        try:
            if f["status"] == "final":
                from .codec import snapshot

                s = snapshot(
                    json.loads(
                        c.execute(
                            "SELECT input_json FROM world_executions WHERE fixture_key=?",
                            (f["key"],),
                        ).fetchone()[0]
                    )["snapshot"]
                )
            else:
                s = adapter(c, f["competition"], policy).pregame(
                    f["key"], logical_hash(c)
                )
            count = [sum(p.eligible for p in t.players) for t in (s.home, s.away)]
            out.append(
                {
                    "fixture": f["key"],
                    "executable": True,
                    "eligible_squads": count,
                    "home": s.home.name,
                    "away": s.away.name,
                }
            )
        except ValueError as error:
            out.append(
                {"fixture": f["key"], "executable": False, "blocker": str(error)}
            )
    return {
        "scope": SCOPE,
        "fixtures": out,
        "passed": len(out) == 16 and all(r["executable"] for r in out),
        "canonical_roster_approval": False,
    }


def player_totals(c):
    totals = {}
    for r in c.execute(
        "SELECT p.*,f.competition FROM world_performances p JOIN world_fixtures f ON f.key=p.fixture_key ORDER BY fixture_key,player_id"
    ):
        p = json.loads(r["performance_json"])
        key = (r["competition"], r["player_id"])
        row = totals.setdefault(
            key,
            {
                "competition": key[0],
                "player_id": key[1],
                "appearances": 0,
                "seconds": 0,
                "goals": 0,
                "assists": 0,
                "shots": 0,
                "xg": 0.0,
            },
        )
        row["appearances"] += 1
        row["seconds"] += p["seconds_played"]
        for k in ("goals", "assists", "shots", "xg"):
            row[k] += p[k]
    for row in totals.values():
        row["xg"] = round(row["xg"], 4)
    return list(totals.values())


def report(directory, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with writer(directory) as (c, policy):
        validation = audit(c, Path(directory) / "parent.sqlite")
        clubs = {r["key"]: r["name"] for r in c.execute("SELECT * FROM world_clubs")}
        matches = [
            {
                "fixture": r["key"],
                "kickoff": r["kickoff"],
                "competition": r["competition"],
                "home": clubs[r["home"]],
                "away": clubs[r["away"]],
                "score": [r["home_goals"], r["away_goals"]],
                "resolution": json.loads(r["resolution_json"]),
            }
            for r in c.execute(
                "SELECT * FROM world_fixtures WHERE status='final' ORDER BY kickoff,key"
            )
        ]
        standings = [
            dict(r)
            for r in c.execute(
                "SELECT c.* FROM clubs c JOIN league_participants p ON p.club_id=c.id WHERE p.season=2027 ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name"
            )
        ]
        preview = fixture_preview(c, policy, "league:332")
        write_json(output / "mirassol_pregame.json", preview)
        write_json(output / "roster_distribution.json", distribution(c))
        write_json(output / "september30_preflight.json", preflight(c, policy))
        public = {
            "scope": SCOPE,
            "official_records_changed": False,
            "accepted_clock": "2027-09-26 23:30",
            "development_clock": c.execute("SELECT clock FROM world_info").fetchone()[
                0
            ],
            "validation": validation,
            "world_sha256": logical_hash(c),
            "canonical_roster_approval": False,
            "modeled_clubs": len(distribution(c)),
            "modeled_players": c.execute(
                "SELECT count(*) FROM world_players WHERE modeled=1"
            ).fetchone()[0],
            "result_delivery": "Full results/standings are private diagnostics; ordinary narration releases only the selected match through its cursor.",
        }
        write_json(output / "world_progress.json", public)
        private = {
            "scope": SCOPE,
            "spoilers": True,
            "matches": matches,
            "standings": standings,
            "ties": [
                dict(r) for r in c.execute("SELECT * FROM world_ties ORDER BY key")
            ],
            "forward_player_totals": player_totals(c),
            "discipline": [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM world_discipline ORDER BY player_id,competition"
                )
            ],
            "player_state": [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM world_player_state ORDER BY player_id"
                )
            ],
            "payroll": [
                dict(r)
                for r in c.execute("SELECT * FROM payroll_periods ORDER BY period")
            ],
        }
        write_json(output / "private_world_progress.json", private)
        lines = [
            "# " + SCOPE + " — private world progression",
            "",
            "**Diagnostic spoilers: this file includes the noncanonical future Vasco result and resulting league table. It is not normal pregame Hikari context.**",
            "",
            "| Kickoff | Fixture | Match | Score | Qualified club |",
            "|---|---|---|---|---|",
        ]
        for m in matches:
            lines.append(
                f"| {m['kickoff']} | {m['fixture']} | {m['home']} – {m['away']} | {m['score'][0]}–{m['score'][1]} | {clubs.get(m['resolution']['winner'],'Not yet decided')} |"
            )
        lines += [
            "",
            "## Recomputed Brasileirão table",
            "",
            "| Club | P | W | D | L | GF | GA | Pts |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in standings:
            lines.append(
                "| "
                + row["name"]
                + " | "
                + " | ".join(
                    str(row[k])
                    for k in ("played", "wins", "draws", "losses", "gf", "ga", "points")
                )
                + " |"
            )
        lines += [
            "",
            "Player totals, exact before/after operations, discipline and injuries are in the companion JSON and portable checkpoint. Recorded historical counters are preserved; forward totals are scoped explicitly by competition.",
            "",
            "Original accepted checkpoint and its fictional clock remain unchanged. Proposed rosters/rules have no canonical approval. Continental later-round draws remain unresolved conditional reservations.",
            "",
        ]
        (output / "private_world_progress.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
        (output / "README.md").write_text(
            "# "
            + SCOPE
            + "\n\n"
            + f"Validated {validation['continental_final']} continental and {validation['league_final']} league results in an isolated world. The accepted checkpoint and official clock are unchanged.\n\nOpen mirassol_pregame.json for the spoiler-safe Vasco preview. Full result, standings, injury and player-state diagnostics are explicitly private. Do not load private files as normal pregame narration context.\n",
            encoding="utf-8",
        )
    return public


def demo(parent, output, seed="task03b-world-demo-v1"):
    from .storage import create
    from .packages import export_world
    from ..checkpoints import staged_directory, restore_checkpoint

    before = file_sha256(Path(parent))
    with staged_directory(Path(output)) as stage:
        world = stage / "world"
        create(parent, world, seed)
        with writer(world) as (c, policy):
            p = preflight(c, policy)
            write_json(stage / "preflight_before.json", p)
            if not p["passed"]:
                raise ValueError(
                    "September 30 preflight incomplete; do not skip fixtures"
                )
        first = advance(world, before_fixture="league:332")
        with writer(world) as (c, policy):
            write_json(
                stage / "mirassol_before_execution.json",
                fixture_preview(c, policy, "league:332"),
            )
            write_json(
                stage / "before_r26.json",
                {
                    "scope": SCOPE,
                    "audit": first,
                    "clock": c.execute("SELECT clock FROM world_info").fetchone()[0],
                },
            )
        final = advance(world, until="2027-10-03 23:59")
        if (final["continental_final"], final["league_final"]) != (16, 10):
            raise ValueError("Bounded demonstration is incomplete")
        public = report(world, stage / "reports")
        resumed = advance(world, until="2027-10-03 23:59")
        with writer(world) as (c, policy):
            if (
                logical_hash(c) != public["world_sha256"]
                or resumed["groups_this_call"] != 0
            ):
                raise ValueError("Resumption changed the world or rerolled a match")
        exported = export_world(world, stage / "NONCANONICAL_DEV_03B.zip")
        restored = restore_checkpoint(
            stage / "NONCANONICAL_DEV_03B.zip", stage / "independent_restore"
        )
        if not restored["independent_replay"] or restored["acceptance_eligible"]:
            raise ValueError("Development restoration/promotion protection failed")
        if file_sha256(Path(parent)) != before:
            raise ValueError("Accepted parent changed")
        write_json(
            stage / "demonstration.json",
            {
                "scope": SCOPE,
                "parent_sha256_before": before,
                "parent_sha256_after": file_sha256(Path(parent)),
                "archive_sha256": exported["sha256"],
                "world_sha256": public["world_sha256"],
                "continental_matches": 16,
                "league_matches": 10,
                "resumption_changed_results": False,
                "independent_restoration_and_replay": True,
                "promotable": False,
            },
        )
    return {
        "scope": SCOPE,
        "output": str(Path(output).resolve()),
        "continental_matches": 16,
        "league_matches": 10,
        "independent_restoration_and_replay": True,
        "official_records_changed": False,
        "promotable": False,
    }
