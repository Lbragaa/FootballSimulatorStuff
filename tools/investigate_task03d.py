"""Preregistered noncanonical controls; no model fitting to Vasco outcomes."""

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.engine import (
    EngineConfig,
    prepare,
    commit_seeds,
    simulate_match,
    validate_match,
)
from braga_era.engine.models import Player, Team, Coach, Snapshot, CompetitionRules
from braga_era.world.forward_config import ForwardConfig
from braga_era.world.storage import writer, logical_hash
from braga_era.world.runner import context
from braga_era.world.players import projected
from braga_era.world.policy import ReadinessPolicy
from braga_era.checkpoints import write_json
from braga_era.history import digest


def trial(snapshot, config, seed, risks=None):
    seeds = commit_seeds(snapshot, config, seed)
    plans = prepare(snapshot, config, seeds)
    if risks:
        plans = tuple(replace(p, risk=r) for p, r in zip(plans, risks))
    result = simulate_match(snapshot, plans, config, seeds)
    checked = validate_match(snapshot, result, config)
    if not checked.ok:
        raise ValueError(checked.errors)
    return result


def count_result(result):
    c = Counter(matches=1)
    c[
        (
            "H"
            if result.score[0] > result.score[1]
            else "D" if result.score[0] == result.score[1] else "A"
        )
    ] += 1
    reds = [e for e in result.events if e.kind == "RED_CARD"]
    c["any_dismissal"] = bool(reds)
    c["dismissals"] = len(reds)
    c["straight_red"] = sum(e.details["reason"] == "straight red" for e in reds)
    c["second_yellow"] = sum(e.details["reason"] == "second yellow" for e in reds)
    c["injuries"] = sum(p.injured for p in result.performances)
    c["yellows"] = sum(p.yellows for p in result.performances)
    c["goals"] = sum(result.score)
    c["shots"] = len(result.shots)
    c["xg"] = sum(s.xg for s in result.shots)
    return c


def synthetic():
    teams = []
    for side in (0, 1):
        key = f"synthetic:{side}"
        players = []
        for i, pos in enumerate(["GK"] * 3 + ["DF"] * 8 + ["MF"] * 8 + ["FW"] * 7):
            players.append(
                Player(
                    10000 + side * 100 + i,
                    key,
                    f"Synthetic {side}-{i}",
                    pos,
                    72,
                    78 if pos == "FW" else 72,
                    78 if pos == "DF" else 72,
                    72,
                    72,
                    72,
                    80 if pos == "GK" else 15,
                    90,
                    65,
                )
            )
        teams.append(
            Team(
                key,
                f"Control {side}",
                72,
                0,
                tuple(players),
                Coach(decision_noise=0, continuity_preference=0),
            )
        )
    return Snapshot(
        "controlled",
        "2027-10-03 16:00",
        "2027-10-03 16:00",
        *teams,
        CompetitionRules("CONTROL"),
        "0" * 64,
        synthetic=True,
    )


def run(directory, n):
    with writer(directory) as (c, p):
        f = c.execute("SELECT * FROM world_fixtures WHERE key='league:333'").fetchone()
        base, _, _ = context(c, f, p, logical_hash(c))
    breakdown = defaultdict(Counter)
    players = Counter()
    clubs = Counter()
    states = Counter()
    positions = Counter()
    player_positions = {
        p.id: p.position for t in (base.home, base.away) for p in t.players
    }
    for cfg in (EngineConfig(), ForwardConfig()):
        for gap in (-15, 0, 15):
            for i in range(200):
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
                snap = replace(
                    base,
                    fixture_key=f"calibration:{gap}:{i}",
                    home=home,
                    away=away,
                    synthetic=True,
                )
                result = trial(snap, cfg, f"task03c-calibration-v1:{gap}:{i}")
                breakdown[f"{cfg.version}:gap{gap}"].update(count_result(result))
                for e in result.events:
                    if e.kind != "RED_CARD":
                        continue
                    players[str(e.player_id)] += 1
                    clubs[e.club_key] += 1
                    positions[player_positions[e.player_id]] += 1
                    own = 0 if e.club_key == snap.home.key else 1
                    state = (
                        "level"
                        if e.pre_score[own] == e.pre_score[1 - own]
                        else (
                            "leading"
                            if e.pre_score[own] > e.pre_score[1 - own]
                            else "trailing"
                        )
                    )
                    states[state] += 1
    controls = {}
    base = synthetic()
    cases = [
        ("identical", 0, 0, False, ("balanced", "balanced")),
        ("reversed", 0, 0, True, ("balanced", "balanced")),
        ("strength_only_3", 3, 0, False, ("balanced", "balanced")),
        ("strength_only_15", 15, 0, False, ("balanced", "balanced")),
        ("players_only_3", 0, 3, False, ("balanced", "balanced")),
        ("players_only_15", 0, 15, False, ("balanced", "balanced")),
        ("both_3", 3, 3, False, ("balanced", "balanced")),
        ("both_15", 15, 15, False, ("balanced", "balanced")),
        ("attacking_cautious", 0, 0, False, ("attacking", "cautious")),
        ("cautious_attacking", 0, 0, False, ("cautious", "attacking")),
    ]
    for name, strength, quality, reverse, risks in cases:
        h, a = (base.away, base.home) if reverse else (base.home, base.away)
        h = replace(
            h,
            strength=72 + strength / 2,
            players=tuple(
                replace(
                    p,
                    ovr=p.ovr + quality / 2,
                    attack=p.attack + quality / 2,
                    defense=p.defense + quality / 2,
                    passing=p.passing + quality / 2,
                    physical=p.physical + quality / 2,
                    composure=p.composure + quality / 2,
                    goalkeeping=p.goalkeeping + quality / 2,
                )
                for p in h.players
            ),
        )
        a = replace(
            a,
            strength=72 - strength / 2,
            players=tuple(
                replace(
                    p,
                    ovr=p.ovr - quality / 2,
                    attack=p.attack - quality / 2,
                    defense=p.defense - quality / 2,
                    passing=p.passing - quality / 2,
                    physical=p.physical - quality / 2,
                    composure=p.composure - quality / 2,
                    goalkeeping=p.goalkeeping - quality / 2,
                )
                for p in a.players
            ),
        )
        total = Counter()
        for i in range(n):
            snap = replace(base, fixture_key=f"03d:{name}:{i}", home=h, away=a)
            total.update(
                count_result(
                    trial(
                        snap, ForwardConfig(), f"task03d-controls-v1:{name}:{i}", risks
                    )
                )
            )
        controls[name] = dict(total)
    alternatives = {}
    configs = [
        ForwardConfig(),
        replace(ForwardConfig(), version="ANALYSIS-03D-yellow-1.2", yellow_lambda=1.2),
        replace(
            ForwardConfig(),
            version="ANALYSIS-03D-yellow-cap-2",
            maximum_yellow_events_per_team=2,
        ),
        replace(
            ForwardConfig(),
            version="ANALYSIS-03D-straight-.015",
            straight_red_probability_per_team=0.015,
        ),
    ]
    for cfg in configs:
        total = Counter()
        for i in range(n):
            total.update(
                count_result(
                    trial(
                        replace(base, fixture_key=f"03d-cards:{i}"),
                        cfg,
                        f"task03d-card-alternatives-v1:{i}",
                        ("balanced", "balanced"),
                    )
                )
            )
        alternatives[cfg.version] = dict(total)
    fatigue = {}
    for weight in (0.05, 0.12):
        cfg = replace(
            ForwardConfig(),
            version=f"ANALYSIS-03D-fatigue-{weight}",
            lineup_fitness_weight=weight,
            injury_probability_per_match=0,
            yellow_lambda=0,
            straight_red_probability_per_team=0,
        )
        snap = base
        rows = []
        prior = set()
        for i in range(24):
            kickoff = (datetime(2027, 10, 1, 16) + timedelta(days=i * 3)).isoformat(
                " ", timespec="minutes"
            )
            if i:
                snap = replace(
                    snap,
                    home=replace(
                        snap.home,
                        players=tuple(
                            replace(
                                p,
                                fitness=projected(
                                    {
                                        "fitness": p.fitness,
                                        "observed_at": snap.kickoff,
                                        "injury_until": None,
                                    },
                                    kickoff,
                                    ReadinessPolicy(),
                                )["fitness"],
                            )
                            for p in snap.home.players
                        ),
                    ),
                    away=replace(
                        snap.away,
                        players=tuple(
                            replace(p, fitness=min(100, p.fitness + 4.5))
                            for p in snap.away.players
                        ),
                    ),
                )
            snap = replace(
                snap,
                fixture_key=f"fatigue:{i}",
                kickoff=kickoff,
                rules=CompetitionRules("LIB" if i % 2 else "LEAGUE"),
            )
            result = trial(snap, cfg, f"task03d-fatigue-v1:{i}")
            starters = set(result.plans[0].starters)
            rows.append(
                {
                    "fixture": i,
                    "mean_home_starter_fitness": statistics.mean(
                        p.fitness for p in snap.home.players if p.id in starters
                    ),
                    "changes": len(starters - prior) if prior else 0,
                    "minimum_home_fitness": min(p.fitness for p in snap.home.players),
                }
            )
            perf = {p.player_id: p for p in result.performances}

            def update(team):
                return replace(
                    team,
                    players=tuple(
                        (
                            replace(
                                p,
                                fitness=perf[p.id].fitness_after,
                                morale=perf[p.id].morale_after,
                                form=perf[p.id].form_after,
                                recent_ratings=(
                                    (perf[p.id].rating, perf[p.id].seconds_played / 60),
                                )
                                + p.recent_ratings[:3],
                            )
                            if p.id in perf
                            else p
                        )
                        for p in team.players
                    ),
                )

            snap = replace(snap, home=update(snap.home), away=update(snap.away))
            prior = starters
        fatigue[str(weight)] = rows
    selection = {}
    for weight in (0.05, 0.12):
        modified = []
        for p in base.home.players:
            if p.position == "FW":
                slot = p.id - 10019
                p = replace(
                    p,
                    ovr=80 if slot == 0 else 78 if slot in (1, 2, 3) else 60,
                    fitness=55 if slot == 0 else 90,
                )
            modified.append(p)
        snap = replace(base, home=replace(base.home, players=tuple(modified)))
        cfg = replace(
            ForwardConfig(),
            version=f"ANALYSIS-03D-selection-{weight}",
            lineup_fitness_weight=weight,
        )
        plan = prepare(
            snap, cfg, commit_seeds(snap, cfg, "task03d-selection-controlled-v1")
        )[0]
        suspended = replace(
            snap,
            home=replace(
                snap.home,
                players=tuple(
                    (
                        replace(
                            p,
                            eligible=False,
                            exclusion_reasons=("simulated suspension",),
                        )
                        if p.id == 10019
                        else p
                    )
                    for p in snap.home.players
                ),
            ),
        )
        excluded = prepare(
            suspended,
            cfg,
            commit_seeds(suspended, cfg, "task03d-selection-exclusion-v1"),
        )[0]
        selection[str(weight)] = {
            "tired_80_ovr_star_starts": 10019 in plan.starters,
            "three_fit_78_ovr_alternatives_available": True,
            "suspended_star_excluded": 10019 not in excluded.starters + excluded.bench,
        }
    return {
        "scope": "NONCANONICAL DEVELOPMENT TEST",
        "policy": "task03d-controlled-analysis-v1",
        "trials_per_control": n,
        "original_1200_breakdown": {k: dict(v) for k, v in breakdown.items()},
        "dismissals_by_player": dict(players),
        "dismissals_by_club": dict(clubs),
        "dismissals_by_score_state": dict(states),
        "dismissals_by_position": dict(positions),
        "controls": controls,
        "analysis_only_card_alternatives": alternatives,
        "fitness_24_matches_every_3_days_no_medical_or_cards": fatigue,
        "fitness_weight_selection_controls": selection,
        "uncertainty": "Maximum binomial 95% half-width about "
        + str(round(1.96 * (0.25 / n) ** 0.5, 4))
        + "; synthetic experiments are not independent real-football observations",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = run(a.directory, a.n)
    write_json(a.output, r)
    print({"output": str(a.output), "sha256": digest(r)})
