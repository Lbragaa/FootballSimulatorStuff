"""Repeatable NONCANONICAL Monte Carlo, never an outcome-selection tool."""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.engine import (
    EngineConfig,
    commit_seeds,
    prepare,
    simulate_match,
    validate_match,
)
from braga_era.history import digest
from braga_era.db import connect_read_only
from braga_era.checkpoints import write_json
from braga_era.world.storage import writer, logical_hash
from braga_era.world.runner import context
from braga_era.world.forward_config import ForwardConfig


def summarize(values):
    data = sorted(values)
    return {
        "mean": round(statistics.mean(data), 5),
        "p05": data[int(0.05 * (len(data) - 1))],
        "median": statistics.median(data),
        "p95": data[int(0.95 * (len(data) - 1))],
    }


def run(directory, count=1000):
    if count < 100:
        raise ValueError("Calibration needs at least 100 fixtures")
    with writer(directory) as (c, policy):
        f = c.execute("SELECT * FROM world_fixtures WHERE key='league:333'").fetchone()
        base, _, _ = context(c, f, policy, logical_hash(c))
        rosters = []
        for club in c.execute("SELECT * FROM world_clubs ORDER BY key"):
            rows = [
                json.loads(r[0])
                for r in c.execute(
                    "SELECT attributes_json FROM world_players WHERE club_key=? AND modeled=1 ORDER BY id",
                    (club["key"],),
                )
            ]
            if not rows:
                continue
            rosters.append(
                {
                    "club": club["key"],
                    "strength": club["strength"],
                    "depth": len(rows),
                    "positions": dict(Counter(r["position"] for r in rows)),
                    "ovr": summarize([r["ovr"] for r in rows]),
                    "gk_ovr": summarize(
                        [r["ovr"] for r in rows if r["position"] == "GK"]
                    ),
                    "reserve_gap": round(
                        statistics.mean(sorted(r["ovr"] for r in rows)[-11:])
                        - statistics.mean(sorted(r["ovr"] for r in rows)[:-11]),
                        3,
                    ),
                }
            )
    with connect_read_only(Path(directory) / "parent.sqlite") as c:
        historical = {}
        for (competition,) in c.execute(
            "SELECT DISTINCT competition FROM fixtures WHERE status='final' ORDER BY competition"
        ):
            rows = c.execute(
                "SELECT home_goals,away_goals FROM fixtures WHERE status='final' AND competition=?",
                (competition,),
            ).fetchall()
            historical[competition] = {
                "n": len(rows),
                "goals": summarize([sum(r) for r in rows]),
                "HDA": [
                    sum((r[0] > r[1], r[0] == r[1], r[0] < r[1])[i] for r in rows)
                    / len(rows)
                    for i in range(3)
                ],
            }
    groups = {}
    for cfg in (EngineConfig(), ForwardConfig()):
        for gap in (-15, 0, 15):
            counters = Counter()
            goals = []
            shots = []
            xgs = []
            ratings = []
            fitness = []
            scorelines = Counter()
            selected = []
            n = count // 6
            for i in range(n):
                home = replace(
                    base.home,
                    strength=72 + gap / 2,
                    form=0,
                    players=tuple(
                        replace(
                            p,
                            ovr=p.ovr + gap / 4,
                            attack=p.attack + gap / 4,
                            fitness=90,
                            morale=65,
                            form=6.55,
                        )
                        for p in base.home.players
                    ),
                )
                away = replace(
                    base.away,
                    strength=72 - gap / 2,
                    form=0,
                    players=tuple(
                        replace(
                            p,
                            ovr=p.ovr - gap / 4,
                            attack=p.attack - gap / 4,
                            fitness=90,
                            morale=65,
                            form=6.55,
                        )
                        for p in base.away.players
                    ),
                )
                snapshot = replace(
                    base,
                    fixture_key=f"calibration:{gap}:{i}",
                    home=home,
                    away=away,
                    synthetic=True,
                )
                seeds = commit_seeds(snapshot, cfg, f"task03c-calibration-v1:{gap}:{i}")
                plans = prepare(snapshot, cfg, seeds)
                result = simulate_match(snapshot, plans, cfg, seeds)
                validation = validate_match(snapshot, result, cfg)
                if not validation.ok:
                    raise ValueError(validation.errors)
                h, a = result.score
                counters["H" if h > a else "D" if h == a else "A"] += 1
                counters["injuries"] += sum(p.injured for p in result.performances)
                counters["reds"] += sum(p.red for p in result.performances)
                counters["yellows"] += sum(p.yellows for p in result.performances)
                goals.append(h + a)
                shots.append(len(result.shots))
                xgs.append(round(sum(s.xg for s in result.shots), 4))
                ratings.extend(p.rating for p in result.performances)
                fitness.extend(p.fitness_after for p in result.performances)
                scorelines[f"{h}-{a}"] += 1
                selected.append(digest([asdict(p) for p in plans]))
            groups[f"{cfg.version}:gap{gap}"] = {
                "n": n,
                "counts": dict(counters),
                "HDA": [round(counters[k] / n, 5) for k in "HDA"],
                "binomial_95_halfwidth_max": round(1.96 * (0.25 / n) ** 0.5, 4),
                "goals": summarize(goals),
                "shots": summarize(shots),
                "xg": summarize(xgs),
                "ratings": summarize(ratings),
                "postmatch_fitness": summarize(fitness),
                "scorelines": dict(sorted(scorelines.items())),
                "distinct_lineups": len(set(selected)),
            }
    return {
        "scope": "NONCANONICAL DEVELOPMENT TEST",
        "policy": "task03c-calibration-v1",
        "actual_fixtures": sum(r["n"] for r in groups.values()),
        "seed_policy": "fixed task03c-calibration-v1:gap:index; no outcome selection",
        "groups": groups,
        "recorded_history": historical,
        "modeled_rosters": rosters,
        "limitations": [
            "Historical coverage is selected, not an independent representative sample",
            "Club and player quality are varied together; this is sensitivity analysis, not parameter identification",
            "Rare-event uncertainty is large; zero observations do not imply zero risk",
            "No real-world squads/results or desired Vasco outcomes were used",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.directory, args.count)
    write_json(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "fixtures": report["actual_fixtures"],
                "sha256": digest(report),
            }
        )
    )
