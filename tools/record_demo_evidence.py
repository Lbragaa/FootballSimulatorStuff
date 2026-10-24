"""Export two completed, validated NONCANONICAL runs as inspectable text evidence."""

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.db import connect_read_only
from braga_era.engine.world import World, MissingRoster
from braga_era.history import digest


def record(db, league, synthetic, output):
    output.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NONCANONICAL TEST SIMULATION — complete demonstrations",
        "",
        "Diagnostic evidence contains complete results and future spoilers. For normal Hikari delivery use the generated sandbox preview and sequential `narrate` command. No official result, table, player state, checkpoint or fictional date changes.",
        "",
    ]
    for name, directory in (("league333", league), ("vasco_synthetic", synthetic)):
        report = json.loads(
            (directory / "private_match_report.json").read_text(encoding="utf-8")
        )
        if (
            not report["validation"]["ok"]
            or report["official"]
            or digest(report["result"]) != report["result_sha256"]
        ):
            raise ValueError("Invalid demonstration")
        for source, target in (
            ("private_match_report.json", name + ".json"),
            ("private_events.jsonl", name + "_events.jsonl"),
            ("preview.json", name + "_preview.json"),
        ):
            shutil.copyfile(directory / source, output / target)
        s = report["snapshot"]
        r = report["result"]
        final = report["sealed_postmatch_summary"]
        names = {
            p["id"]: p["name"] for t in (s["home"], s["away"]) for p in t["players"]
        }
        title = (
            f"{s['home']['name']} {r['score'][0]}–{r['score'][1]} {s['away']['name']}"
        )
        lines.extend(
            [
                f"## {title}",
                "",
                f"Fixture `{s['fixture_key']}`; proposed kickoff {s['kickoff']}; observed state {s['as_of']}; synthetic={s['synthetic']}. Engine `{r['engine_version']}`.",
                "",
                f"Requested seed `{r['seeds']['requested_seed']}`; root `{r['seeds']['root_sha256']}`; result `{report['result_sha256']}`. Seed stored before draws; no outcome-based retry.",
                "",
                f"Independent replay: {report['validation']['checks']} checks, zero failures. Source/scratch DB SHA256 unchanged: `{report['database_guard']['before_sha256']}`.",
                "",
                "| Team | Shots | On target | xG | Yellow | Red | Substitutions |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for team, stats in zip((s["home"], s["away"]), final["team_stats"]):
            lines.append(
                "| "
                + team["name"]
                + " | "
                + " | ".join(
                    str(stats[k])
                    for k in (
                        "shots",
                        "on_target",
                        "xg",
                        "yellow_cards",
                        "red_cards",
                        "substitutions",
                    )
                )
                + " |"
            )
        lines.extend(
            [
                "",
                f"Possession home: {r['possession_home']}%. Prematch H/D/A: {r['prematch']['home_win_probability']:.2%} / {r['prematch']['draw_probability']:.2%} / {r['prematch']['away_win_probability']:.2%}; expected xG {r['prematch']['expected_xg']}.",
                "",
            ]
        )
        for team, plan in zip((s["home"], s["away"]), r["plans"]):
            lines.extend(
                [
                    f"### {team['name']} — {plan['formation']}, {plan['risk']}",
                    "",
                    "XI: "
                    + ", ".join(f"{names[p]} #{p}" for p in plan["starters"])
                    + ".",
                    "",
                    "Bench: "
                    + ", ".join(f"{names[p]} #{p}" for p in plan["bench"])
                    + ".",
                    "",
                ]
            )
        lines.extend(
            [
                "### Complete authoritative event sequence",
                "",
                "| Sequence | Clock | Event | Actor | Score after | Details |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for e in r["events"]:
            clock = f"{e['elapsed_seconds']//60}:{e['elapsed_seconds']%60:02}"
            details = json.dumps(
                e["details"], ensure_ascii=False, sort_keys=True
            ).replace("|", "/")
            lines.append(
                f"| {e['sequence']} | {clock} | {e['kind']} | {names.get(e['player_id'],'—')} | {e['post_score'][0]}–{e['post_score'][1]} | `{details}` |"
            )
        lines.extend(
            [
                "",
                "### Proposed postmatch player state (not persisted)",
                "",
                "| ID | Player | Seconds | G | A | Rating | Fitness before→after | Form before→after |",
                "|---:|---|---:|---:|---:|---:|---|---|",
            ]
        )
        for p in r["performances"]:
            lines.append(
                f"| {p['player_id']} | {names[p['player_id']]} | {p['seconds_played']} | {p['goals']} | {p['assists']} | {p['rating']} | {p['fitness_before']}→{p['fitness_after']} | {p['form_before']}→{p['form_after']} |"
            )
        lines.append("")
    with connect_read_only(db) as c:
        rows = [
            dict(r)
            for r in c.execute(
                "SELECT event_id,competition,home,away,kickoff FROM calendar_events WHERE kickoff LIKE '2027-09-30%' AND status='scheduled' ORDER BY kickoff,event_id"
            )
        ]
    preflight = []
    for row in rows:
        try:
            World(db).load_pregame("calendar:" + row["event_id"])
        except MissingRoster as error:
            preflight.append({**row, "executable": False, "blocker": str(error)})
        else:
            raise ValueError(
                "Continental roster availability changed; review fallback evidence"
            )
    (output / "september30_preflight.json").write_text(
        json.dumps(
            {
                "scope": "READ-ONLY PREFLIGHT",
                "fixtures": preflight,
                "fallback": "league:333; no foreign player data invented",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines.extend(
        [
            "## September 30 preflight",
            "",
            f"{len(preflight)} scheduled continental fixtures fail closed because foreign player squads are absent. The real-fixture sandbox uses league:333, the first scheduled non-Vasco league fixture with two recorded eligible squads. This isolated test does not execute or skip any official calendar event. See `september30_preflight.json` for every fixture and exact blocker.",
            "",
        ]
    )
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "reports": 2,
                "continental_preflight_blockers": len(preflight),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--league", type=Path, required=True)
    parser.add_argument("--synthetic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record(args.db, args.league, args.synthetic, args.output)
