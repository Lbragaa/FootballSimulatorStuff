"""Pure stochastic regulation match engine. No SQLite, filesystem or UI writes."""

from math import exp, factorial, sqrt

from .models import Event, Shot, Performance, Prematch, MatchResult, SCOPE
from .randomness import stream, verify_commitment
from .validation import validate_plans


def clamp(value, low, high):
    return max(low, min(high, value))


def poisson(rng, lam):
    cutoff = exp(-max(0, lam))
    product = 1.0
    count = 0
    while product > cutoff:
        count += 1
        product *= rng.random()
    return max(0, count - 1)


def finishing_probability(xg, shooter, goalie, config):
    skills = clamp(
        1
        + config.composure_probability_weight * (shooter.composure - 72)
        + config.finishing_attack_weight * (shooter.attack - 72)
        - config.goalkeeper_probability_weight * (goalie.goalkeeping - 72),
        0.65,
        1.35,
    )
    return clamp(
        xg * (1 + config.finishing_form_weight * (shooter.form - 6.55)) * skills,
        0.006,
        0.82,
    )


def prematch(snapshot, plans, config):
    values = []
    for team, plan in zip((snapshot.home, snapshot.away), plans):
        lookup = {p.id: p for p in team.players}
        xi = [lookup[i] for i in plan.starters]
        quality = (
            config.club_quality_weight * team.strength
            + config.xi_quality_weight * sum(p.ovr for p in xi) / 11
            + config.team_form_weight * team.form
            + config.individual_form_weight * sum(p.form - 6.55 for p in xi) / 11
            + config.fitness_quality_weight * (sum(p.fitness for p in xi) / 11 - 87)
        )
        values.append(quality)
    hx = clamp(
        config.home_base_xg + config.quality_difference_xg * (values[0] - values[1]),
        0.45,
        2.55,
    )
    ax = clamp(
        config.away_base_xg + config.quality_difference_xg * (values[1] - values[0]),
        0.38,
        2.30,
    )
    targets = [hx, ax]
    for side, plan in enumerate(plans):
        if plan.risk == "attacking":
            targets[side] += 0.08
            targets[1 - side] += 0.04
        elif plan.risk == "cautious":
            targets[side] -= 0.10
            targets[1 - side] -= 0.08
    targets = [round(clamp(x, 0.30, 3.2), 4) for x in targets]
    probabilities = [0.0, 0.0, 0.0]
    for h in range(13):
        hp = exp(-targets[0]) * targets[0] ** h / factorial(h)
        for a in range(13):
            p = hp * exp(-targets[1]) * targets[1] ** a / factorial(a)
            probabilities[0 if h > a else 1 if h == a else 2] += p
    total = sum(probabilities)
    return Prematch(
        round(values[0], 4),
        round(values[1], 4),
        tuple(targets),
        *(round(p / total, 12) for p in probabilities)
    )


def simulate_match(snapshot, plans, config, seeds):
    if snapshot.scope != SCOPE:
        raise ValueError("Only noncanonical sandbox execution is authorized")
    config.validate()
    verify_commitment(snapshot, config, seeds)
    issues = validate_plans(snapshot, plans)
    if issues:
        raise ValueError("Invalid match plans: " + "; ".join(issues))
    if snapshot.rules.extra_time_if_tied or snapshot.rules.penalties_if_tied:
        raise NotImplementedError(
            "Phase 2A simulates regulation only; competition resolution belongs to Task 03B"
        )
    teams = (snapshot.home, snapshot.away)
    players = {p.id: p for t in teams for p in t.players}
    keys = [t.key for t in teams]
    lookup_side = {key: i for i, key in enumerate(keys)}
    active = [set(plan.starters) for plan in plans]
    benches = [set(plan.bench) for plan in plans]
    risk = [p.risk for p in plans]
    used_subs = [0, 0]
    sub_windows = [set(), set()]
    score = [0, 0]
    end = (90 + config.stoppage_minutes) * 60
    events = []
    shots = []
    stats = {}
    entry = {}
    initial = prematch(snapshot, plans, config)
    rng_chances = stream(seeds, "chance-generation")
    rng_actor = stream(seeds, "attribution")
    rng_goal = stream(seeds, "finishing")
    rng_cards = stream(seeds, "discipline")
    rng_injury = stream(seeds, "injuries")
    rng_coach = stream(seeds, "live-coaches")
    rng_post = stream(seeds, "postmatch")

    def start(pid, side, time, starter):
        entry[pid] = time
        stats[pid] = {
            "side": side,
            "starter": starter,
            "seconds": 0,
            "goals": 0,
            "assists": 0,
            "shots": 0,
            "on_target": 0,
            "xg": 0.0,
            "saves": 0,
            "yellows": 0,
            "red": False,
            "injured": False,
        }

    for side, plan in enumerate(plans):
        for pid in plan.starters:
            start(pid, side, 0, True)

    def emit(time, kind, side=None, pid=None, details=None, before=None):
        period = "1" if time < 2700 or kind == "HALF_TIME" else "2"
        events.append(
            Event(
                len(events) + 1,
                time,
                period,
                kind,
                keys[side] if side is not None else None,
                pid,
                tuple(score) if before is None else before,
                tuple(score),
                tuple(sorted(active[0])),
                tuple(sorted(active[1])),
                details or {},
            )
        )

    def leave(pid, time):
        stats[pid]["seconds"] += time - entry.pop(pid)

    def substitute(side, outgoing, incoming, time, reason):
        active[side].remove(outgoing)
        leave(outgoing, time)
        benches[side].remove(incoming)
        active[side].add(incoming)
        start(incoming, side, time, False)
        used_subs[side] += 1
        sub_windows[side].add(time)
        emit(
            time,
            "SUBSTITUTION",
            side,
            incoming,
            {"outgoing_id": outgoing, "reason": reason},
        )

    def incoming_for(side, position):
        pool = [
            players[p] for p in sorted(benches[side]) if players[p].position == position
        ]
        if not pool:
            return None
        return max(
            pool,
            key=lambda p: (
                p.ovr
                + 0.03 * p.fitness
                + 2 * (p.form - 6.55)
                + rng_coach.gauss(0, 0.5),
                -p.id,
            ),
        ).id

    timeline = []
    serial = 0

    def schedule(time, priority, kind, side=None, data=None):
        nonlocal serial
        serial += 1
        timeline.append((time, priority, serial, kind, side, data))

    for side, team in enumerate(teams):
        n = int(
            clamp(
                poisson(
                    rng_chances,
                    config.shot_count_lambda
                    + config.shot_strength_coefficient * (team.strength - 72),
                ),
                config.shot_minimum,
                config.shot_maximum,
            )
        )
        raw = [
            clamp(
                rng_chances.betavariate(config.chance_beta_a, config.chance_beta_b),
                0.016,
                0.45,
            )
            for _ in range(n)
        ]
        for value in raw:
            xg = round(
                clamp(value * initial.expected_xg[side] / sum(raw), 0.014, 0.68), 4
            )
            time = rng_chances.randint(180, end - 1)
            if time == 2700:
                time += 1
            schedule(time, 4, "CHANCE", side, xg)
        for minute in plans[side].substitution_minutes:
            schedule(minute * 60, 1, "COACH", side)
        for _ in range(
            min(
                config.maximum_yellow_events_per_team,
                poisson(rng_cards, config.yellow_lambda),
            )
        ):
            schedule(rng_cards.randint(600, end - 1), 3, "CARD", side)
        if rng_cards.random() < config.straight_red_probability_per_team:
            schedule(rng_cards.randint(600, end - 1), 3, "STRAIGHT_RED", side)
    if rng_injury.random() < config.injury_probability_per_match:
        schedule(rng_injury.randint(300, end - 1), 2, "HURT", rng_injury.randrange(2))
    schedule(2700, -2, "HALF_TIME")
    schedule(2700, -1, "SECOND_HALF_KICKOFF")
    emit(0, "KICKOFF", details={"duration_seconds": end, "scope": snapshot.scope})

    for time, _, _, kind, side, data in sorted(timeline):
        if kind in ("HALF_TIME", "SECOND_HALF_KICKOFF"):
            emit(time, kind)
            continue
        if kind == "COACH":
            desired = (
                "attacking"
                if score[side] < score[1 - side]
                else (
                    "cautious"
                    if score[side] > score[1 - side] and time >= 70 * 60
                    else risk[side]
                )
            )
            if desired != risk[side]:
                old = risk[side]
                risk[side] = desired
                emit(
                    time,
                    "TACTICAL_CHANGE",
                    side,
                    details={
                        "before": old,
                        "after": desired,
                        "reason": "Autonomous live score/workload decision",
                    },
                )
            if (
                not benches[side]
                or used_subs[side] >= config.maximum_substitutions
                or len(sub_windows[side]) >= config.maximum_substitution_windows
                and time not in sub_windows[side]
            ):
                continue
            if not any(players[p].position == "GK" for p in active[side]):
                new = incoming_for(side, "GK")
                old = min(
                    (p for p in active[side]), key=lambda p: (players[p].fitness, p)
                )
                if new is not None:
                    substitute(side, old, new, time, "replace dismissed goalkeeper")
                continue
            preferred = (
                ("FW", "MF", "DF")
                if score[side] <= score[1 - side]
                else ("MF", "DF", "FW")
            )
            for position in preferred:
                outgoing = [
                    p for p in sorted(active[side]) if players[p].position == position
                ]
                new = incoming_for(side, position)
                if outgoing and new is not None:
                    old = min(
                        outgoing,
                        key=lambda p: (
                            players[p].fitness
                            + 1.5 * (players[p].form - 6.55)
                            + 2 * stats[p]["goals"]
                            - 4 * stats[p]["yellows"],
                            p,
                        ),
                    )
                    substitute(side, old, new, time, "score-aware positional refresh")
                    break
        elif kind in ("CARD", "STRAIGHT_RED"):
            ids = sorted(active[side])
            pid = rng_cards.choices(
                ids,
                weights=[
                    {"GK": 0.2, "DF": 2, "MF": 1.5, "FW": 0.6}[players[p].position]
                    for p in ids
                ],
            )[0]
            if kind == "CARD":
                stats[pid]["yellows"] += 1
                emit(
                    time,
                    "YELLOW_CARD",
                    side,
                    pid,
                    {"yellow_count": stats[pid]["yellows"]},
                )
                if stats[pid]["yellows"] < 2:
                    continue
            active[side].remove(pid)
            leave(pid, time)
            stats[pid]["red"] = True
            emit(
                time,
                "RED_CARD",
                side,
                pid,
                {"reason": "second yellow" if kind == "CARD" else "straight red"},
            )
        elif kind == "HURT":
            pid = rng_injury.choice(sorted(active[side]))
            stats[pid]["injured"] = True
            emit(
                time,
                "INJURY",
                side,
                pid,
                {
                    "description": "minor muscle strain",
                    "absence_days": config.injury_absence_days,
                },
            )
            legal_window = (
                len(sub_windows[side]) < config.maximum_substitution_windows
                or time in sub_windows[side]
            )
            new = (
                incoming_for(side, players[pid].position)
                if used_subs[side] < config.maximum_substitutions and legal_window
                else None
            )
            if new is not None:
                substitute(side, pid, new, time, "injury replacement")
            else:
                active[side].remove(pid)
                leave(pid, time)
                emit(
                    time,
                    "WITHDRAWAL",
                    side,
                    pid,
                    {"reason": "injury; no legal replacement"},
                )
        elif kind == "CHANCE":
            ids = [p for p in sorted(active[side]) if players[p].position != "GK"]
            if not ids:
                continue
            pid = rng_actor.choices(
                ids,
                weights=[
                    max(0.02, (players[p].attack / 72) ** 2)
                    * {"DF": 0.45, "MF": 2.5, "FW": 6.1}[players[p].position]
                    for p in ids
                ],
            )[0]
            keeper = max(
                sorted(active[1 - side]),
                key=lambda p: (players[p].position == "GK", players[p].goalkeeping, -p),
            )
            live = 1.0
            if risk[side] != plans[side].risk:
                live *= (
                    config.live_attack_xg_multiplier
                    if risk[side] == "attacking"
                    else config.live_caution_xg_multiplier
                )
            if risk[1 - side] != plans[1 - side].risk:
                live *= 1.04 if risk[1 - side] == "attacking" else 0.96
            live *= max(
                0.45, 1 - config.missing_player_xg_penalty * (11 - len(active[side]))
            )
            live *= 1 + 0.075 * (11 - len(active[1 - side]))
            xg = round(clamp(data * live, 0.006, 0.80), 4)
            shooter = players[pid]
            goalie = players[keeper]
            probability = finishing_probability(xg, shooter, goalie, config)
            goal = rng_goal.random() < probability
            on_target = goal or rng_goal.random() < clamp(0.22 + xg * 1.03, 0.20, 0.75)
            assist = None
            if goal and rng_actor.random() < config.assist_probability:
                others = [p for p in sorted(active[side]) if p != pid]
                assist = rng_actor.choices(
                    others,
                    weights=[
                        {"GK": 0.02, "DF": 0.9, "MF": 3.2, "FW": 2.2}[
                            players[p].position
                        ]
                        * (players[p].passing / 72) ** 2
                        for p in others
                    ],
                )[0]
            shot = Shot(
                len(shots) + 1,
                time,
                keys[side],
                pid,
                keeper,
                xg,
                round(probability, 8),
                on_target,
                goal,
                assist,
            )
            shots.append(shot)
            stats[pid]["shots"] += 1
            stats[pid]["xg"] += xg
            stats[pid]["on_target"] += int(on_target)
            emit(
                time,
                "SHOT",
                side,
                pid,
                {
                    "shot_id": shot.id,
                    "xg": xg,
                    "goal_probability": shot.goal_probability,
                    "goalkeeper_id": keeper,
                    "on_target": on_target,
                    "goal": goal,
                },
            )
            if goal:
                previous = tuple(score)
                score[side] += 1
                stats[pid]["goals"] += 1
                if assist is not None:
                    stats[assist]["assists"] += 1
                emit(
                    time,
                    "GOAL",
                    side,
                    pid,
                    {"shot_id": shot.id, "assist_id": assist},
                    before=previous,
                )
            elif on_target:
                stats[keeper]["saves"] += 1
                emit(
                    time,
                    "SAVE",
                    1 - side,
                    keeper,
                    {"shot_id": shot.id, "shooter_id": pid},
                )
    emit(end, "FINAL_WHISTLE")
    for side in (0, 1):
        for pid in sorted(active[side]):
            leave(pid, end)
    performances = []
    for pid, stat in sorted(stats.items()):
        p = players[pid]
        side = stat["side"]
        win = score[side] > score[1 - side]
        loss = score[side] < score[1 - side]
        rating = round(
            clamp(
                6.45
                + 0.033 * (p.ovr - 72)
                + 0.18 * (p.form - 6.55)
                + 0.86 * stat["goals"]
                + 0.55 * stat["assists"]
                + (0.19 if win else -0.17 if loss else 0.04)
                + (0.1 if p.position == "GK" else 0)
                + 0.04 * stat["saves"]
                - 0.1 * stat["yellows"]
                - 0.8 * stat["red"],
                5.2,
                9.8,
            ),
            1,
        )
        loss_fitness = rng_post.uniform(
            config.fitness_loss_min, config.fitness_loss_max
        ) * (stat["seconds"] / 5400)
        if stat["injured"]:
            loss_fitness += 5
        recent = [(rating, stat["seconds"] / 60)] + list(p.recent_ratings[:3])
        weights = [0.68**i * sqrt(min(1, m / 60)) for i, (_, m) in enumerate(recent)]
        newform = 6.55 + (
            sum(w * r for w, (r, _) in zip(weights, recent)) / sum(weights) - 6.55
        ) * min(1, len(recent) / 3)
        performances.append(
            Performance(
                pid,
                keys[side],
                stat["starter"],
                stat["seconds"],
                stat["goals"],
                stat["assists"],
                stat["shots"],
                stat["on_target"],
                round(stat["xg"], 4),
                stat["saves"],
                stat["yellows"],
                stat["red"],
                stat["injured"],
                rating,
                p.fitness,
                round(clamp(p.fitness - loss_fitness, 0, 100), 2),
                p.morale,
                clamp(p.morale + (2 if win else -2 if loss else 0), 0, 100),
                p.form,
                round(newform, 3),
            )
        )
    possession = round(
        clamp(
            51
            + (initial.home_quality - initial.away_quality) * 0.62
            + rng_post.gauss(0, 5),
            36,
            66,
        ),
        1,
    )
    return MatchResult(
        snapshot.fixture_key,
        snapshot.fingerprint,
        config.fingerprint,
        config.version,
        seeds,
        plans,
        initial,
        tuple(score),
        possession,
        tuple(events),
        tuple(shots),
        tuple(performances),
        end,
    )
