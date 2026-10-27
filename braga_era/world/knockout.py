"""Pure proposed tie resolution, reusing regulation chance/finishing and player metrics."""

from dataclasses import asdict
from ..engine.match import clamp, poisson, finishing_probability
from ..engine.metrics import performance
from ..engine.randomness import stream
from ..engine.validation import validate_match
from ..history import digest

VERSION = "braga-knockout-1.0.0"


def resolve(snapshot, result, config, rules, prior=(0, 0)):
    if rules.away_goals:
        raise ValueError(
            "Away-goal resolution requires a separately registered rule version"
        )
    if rules.version != "knockout-proposal-1.0.0":
        raise ValueError("Unsupported knockout rule version")
    score = list(result.score)
    players = {p.id: p for t in (snapshot.home, snapshot.away) for p in t.players}
    keys = [snapshot.home.key, snapshot.away.key]
    active = [
        list(result.events[-1].on_field_home),
        list(result.events[-1].on_field_away),
    ]
    events = [asdict(e) for e in result.events]
    shots = [asdict(s) for s in result.shots]
    perfs = [asdict(p) for p in result.performances]
    duration = result.duration_seconds
    rng = stream(result.seeds, "knockout:" + VERSION)
    extras = []
    kicks = []
    aggregate = lambda: (prior[0] + score[0], prior[1] + score[1])

    def emit(time, kind, side=None, pid=None, details=None, before=None, period="ET"):
        e = {
            "sequence": len(events) + 1,
            "elapsed_seconds": time,
            "period": period,
            "kind": kind,
            "club_key": keys[side] if side is not None else None,
            "player_id": pid,
            "pre_score": list(score) if before is None else before,
            "post_score": list(score),
            "on_field_home": active[0],
            "on_field_away": active[1],
            "details": details or {},
        }
        events.append(e)

    tied = aggregate()[0] == aggregate()[1]
    if tied and (rules.extra_time or rules.penalties):
        events[-1]["kind"] = "REGULATION_END"
    if tied and rules.extra_time:
        emit(duration, "EXTRA_TIME_START")
        timeline = []
        for side in (0, 1):
            count = poisson(rng, config.shot_count_lambda / 3)
            raw = [
                rng.betavariate(config.chance_beta_a, config.chance_beta_b)
                for _ in range(count)
            ]
            for x in raw:
                timeline.append(
                    (
                        duration + rng.randint(1, 1799),
                        side,
                        clamp(
                            x * result.prematch.expected_xg[side] / 3 / sum(raw),
                            0.006,
                            0.68,
                        ),
                    )
                )
        midpoint = False
        for time, side, xg in sorted(timeline):
            if time >= duration + 900 and not midpoint:
                emit(duration + 900, "EXTRA_TIME_INTERVAL")
                midpoint = True
            outfield = [p for p in active[side] if players[p].position != "GK"]
            pid = rng.choices(
                outfield,
                weights=[
                    {"DF": 0.45, "MF": 2.5, "FW": 6.1}[players[p].position]
                    * (players[p].attack / 72) ** 2
                    for p in outfield
                ],
            )[0]
            keeper = max(
                active[1 - side],
                key=lambda p: (players[p].position == "GK", players[p].goalkeeping, -p),
            )
            xg = round(xg, 4)
            prob = round(
                finishing_probability(xg, players[pid], players[keeper], config), 8
            )
            goal = rng.random() < prob
            on_target = goal or rng.random() < clamp(0.22 + xg * 1.03, 0.20, 0.75)
            others = [p for p in active[side] if p != pid]
            assist = (
                rng.choice(others)
                if goal and rng.random() < config.assist_probability
                else None
            )
            shot = {
                "id": len(shots) + 1,
                "elapsed_seconds": time,
                "club_key": keys[side],
                "player_id": pid,
                "goalkeeper_id": keeper,
                "xg": xg,
                "goal_probability": prob,
                "on_target": on_target,
                "goal": goal,
                "assist_id": assist,
            }
            shots.append(shot)
            extras.append(shot)
            emit(
                time,
                "SHOT",
                side,
                pid,
                {
                    "shot_id": shot["id"],
                    "xg": xg,
                    "goal": goal,
                    "on_target": on_target,
                    "goalkeeper_id": keeper,
                    "goal_probability": prob,
                },
            )
            if goal:
                before = list(score)
                score[side] += 1
                emit(
                    time,
                    "GOAL",
                    side,
                    pid,
                    {"shot_id": shot["id"], "assist_id": assist},
                    before,
                )
            elif on_target:
                emit(time, "SAVE", 1 - side, keeper, {"shot_id": shot["id"]})
        if not midpoint:
            emit(duration + 900, "EXTRA_TIME_INTERVAL")
        duration += 1800
        emit(duration, "EXTRA_TIME_END")
        stats = {
            p["player_id"]: {
                "side": keys.index(p["club_key"]),
                "starter": p["starter"],
                "seconds": p["seconds_played"]
                + (1800 if p["player_id"] in active[keys.index(p["club_key"])] else 0),
                **{
                    k: p[k]
                    for k in (
                        "goals",
                        "assists",
                        "shots",
                        "on_target",
                        "xg",
                        "saves",
                        "yellows",
                        "red",
                        "injured",
                    )
                },
            }
            for p in perfs
        }
        for s in extras:
            row = stats[s["player_id"]]
            row["shots"] += 1
            row["on_target"] += int(s["on_target"])
            row["xg"] += s["xg"]
            row["goals"] += int(s["goal"])
            if s["assist_id"] is not None:
                stats[s["assist_id"]]["assists"] += 1
            if s["on_target"] and not s["goal"]:
                stats[s["goalkeeper_id"]]["saves"] += 1
        perfs = [
            asdict(performance(players[pid], stat, score, rng, config))
            for pid, stat in sorted(stats.items())
        ]
    winner = None
    penalty_score = None
    totals = aggregate()
    if rules.penalties and totals[0] == totals[1]:
        emit(duration, "PENALTY_SHOOTOUT_START", period="PEN")
        size = min(map(len, active))
        order = [
            sorted(ids, key=lambda p: (-players[p].composure, -players[p].attack, p))[
                :size
            ]
            for ids in active
        ]
        tally = [0, 0]
        resolved = False
        for round_index in range(64):
            for side in (0, 1):
                pid = order[side][round_index % size]
                keeper = max(
                    active[1 - side],
                    key=lambda p: (
                        players[p].position == "GK",
                        players[p].goalkeeping,
                        -p,
                    ),
                )
                probability = clamp(
                    0.72
                    + 0.003 * (players[pid].composure - 72)
                    - 0.002 * (players[keeper].goalkeeping - 72),
                    0.45,
                    0.9,
                )
                scored = rng.random() < probability
                tally[side] += int(scored)
                duration += 45
                kick = {
                    "side": side,
                    "player_id": pid,
                    "goalkeeper_id": keeper,
                    "scored": scored,
                    "penalty_score": list(tally),
                    "round": round_index + 1,
                }
                kicks.append(kick)
                emit(duration, "PENALTY_KICK", side, pid, kick, period="PEN")
                if round_index < 5:
                    taken = [round_index + 1, round_index + (side == 1)]
                    if tally[0] > tally[1] + (5 - taken[1]) or tally[1] > tally[0] + (
                        5 - taken[0]
                    ):
                        resolved = True
                        break
            if resolved or round_index >= 4 and tally[0] != tally[1]:
                resolved = True
                break
        if not resolved:
            raise ValueError(
                "Unresolved 64-round shootout; retain commitment, fail closed"
            )
        penalty_score = tally
        winner = keys[0 if tally[0] > tally[1] else 1]
    elif rules.penalties:
        winner = keys[0 if totals[0] > totals[1] else 1]
    if events[-1]["kind"] != "FINAL_WHISTLE":
        emit(duration, "FINAL_WHISTLE", period="END")
    resolution = {
        "version": VERSION,
        "rules": asdict(rules),
        "prior_home_away": list(prior),
        "aggregate_home_away": list(aggregate()),
        "winner": winner,
        "penalty_score": penalty_score,
        "kicks": kicks,
        "extra_time_played": bool(extras or rules.extra_time and tied),
        "limitations": "ET retains regulation final XI, with no additional subs/cards/injuries; proposed first integration model",
    }
    return {
        "scope": "NONCANONICAL DEVELOPMENT TEST",
        "engine_version": VERSION,
        "regulation": asdict(result),
        "score": score,
        "shots": shots,
        "performances": perfs,
        "events": events,
        "duration_seconds": duration,
        "resolution": resolution,
    }


def validate_bundle(snapshot, result, config, rules, prior, bundle):
    validation = validate_match(snapshot, result, config)
    if not validation.ok:
        raise ValueError("Regulation replay failed: " + str(validation.errors))
    # Exact deterministic extension replay additionally checks shootout early stopping, ET attribution and merged metrics.
    expected = resolve(snapshot, result, config, rules, prior)
    if digest(expected) != digest(bundle):
        raise ValueError(
            "Knockout resolution, event sequence or player accounting differs from committed replay"
        )
    if rules.penalties and bundle["resolution"]["winner"] not in (
        snapshot.home.key,
        snapshot.away.key,
    ):
        raise ValueError("Decisive match has no qualified club")
    return {
        "ok": True,
        "regulation_checks": validation.checks,
        "extension_replayed": True,
    }
