"""Forward ET model: two 15-minute periods, six substitutions, cards and injuries.

Proposal: one additional live substitution window; intervals use no window.
Shootouts use eligible final players, reduced to equal numbers, never match goals.
"""

from dataclasses import asdict, replace
from ..engine.models import Event, Shot
from ..engine.match import clamp, poisson, finishing_probability
from ..engine.metrics import performance
from ..engine.randomness import stream
from ..engine.validation import validate_match
from ..history import digest
from . import knockout

VERSION = "braga-knockout-2.1.0"


def extra_time(snapshot, result, config, *, version=VERSION):
    rng = stream(result.seeds, version + ":extra-time")
    keys = [snapshot.home.key, snapshot.away.key]
    players = {p.id: p for t in (snapshot.home, snapshot.away) for p in t.players}
    active = [
        set(result.events[-1].on_field_home),
        set(result.events[-1].on_field_away),
    ]
    stats = {
        p.player_id: {
            "side": keys.index(p.club_key),
            "starter": p.starter,
            "seconds": p.seconds_played,
            **{
                k: getattr(p, k)
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
        for p in result.performances
    }
    start = result.duration_seconds
    entered = {pid: start for ids in active for pid in ids}
    benches = [set(p.bench) - set(stats) for p in result.plans]
    substitutions = [
        sum(e.kind == "SUBSTITUTION" and e.club_key == k for e in result.events)
        for k in keys
    ]
    windows = [
        {
            e.elapsed_seconds
            for e in result.events
            if e.kind == "SUBSTITUTION" and e.club_key == k
        }
        for k in keys
    ]
    events = list(result.events[:-1]) + [
        replace(result.events[-1], kind="REGULATION_END")
    ]
    shots = list(result.shots)
    score = list(result.score)

    def emit(time, kind, side=None, pid=None, details=None, before=None):
        events.append(
            Event(
                len(events) + 1,
                time,
                "ET1" if time < start + 900 else "ET2",
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

    def leave(side, pid, time):
        stats[pid]["seconds"] += time - entered.pop(pid)
        active[side].remove(pid)

    def substitute(side, pid, time, interval=False):
        if substitutions[side] >= 6 or (
            not interval and len(windows[side]) >= 4 and time not in windows[side]
        ):
            return False
        position = players[pid].position
        candidates = [p for p in benches[side] if players[p].position == position]
        if not candidates:
            return False
        incoming = max(
            candidates, key=lambda p: (players[p].ovr + 0.12 * players[p].fitness, -p)
        )
        leave(side, pid, time)
        benches[side].remove(incoming)
        active[side].add(incoming)
        entered[incoming] = time
        stats[incoming] = dict(
            side=side,
            starter=False,
            seconds=0,
            goals=0,
            assists=0,
            shots=0,
            on_target=0,
            xg=0.0,
            saves=0,
            yellows=0,
            red=False,
            injured=False,
        )
        substitutions[side] += 1
        if not interval:
            windows[side].add(time)
        emit(
            time,
            "SUBSTITUTION",
            side,
            incoming,
            {
                "outgoing_id": pid,
                "reason": "ET autonomous replacement",
                "interval": interval,
            },
        )
        return True

    def ensure_keeper(side, time):
        if any(players[p].position == "GK" for p in active[side]):
            return
        keepers = [p for p in benches[side] if players[p].position == "GK"]
        if (
            keepers
            and substitutions[side] < 6
            and (len(windows[side]) < 4 or time in windows[side])
        ):
            # Sacrifice a current outfielder; a dismissal never restores the team count.
            outgoing = min(active[side], key=lambda p: (players[p].ovr, p))
            incoming = max(keepers, key=lambda p: (players[p].goalkeeping, -p))
            leave(side, outgoing, time)
            benches[side].remove(incoming)
            active[side].add(incoming)
            entered[incoming] = time
            stats[incoming] = dict(
                side=side,
                starter=False,
                seconds=0,
                goals=0,
                assists=0,
                shots=0,
                on_target=0,
                xg=0.0,
                saves=0,
                yellows=0,
                red=False,
                injured=False,
            )
            substitutions[side] += 1
            windows[side].add(time)
            emit(
                time,
                "SUBSTITUTION",
                side,
                incoming,
                {
                    "outgoing_id": outgoing,
                    "reason": "ET dismissed goalkeeper replacement",
                },
            )
        else:
            keeper = max(active[side], key=lambda p: (players[p].goalkeeping, -p))
            emit(
                time,
                "EMERGENCY_GOALKEEPER",
                side,
                keeper,
                {"reason": "no legal goalkeeper replacement"},
            )

    timeline = [
        (start, 0, "EXTRA_TIME_START", None, None),
        (start + 900, 0, "EXTRA_TIME_INTERVAL", None, None),
    ]
    for side in (0, 1):
        for boundary in (start, start + 900):
            timeline.append((boundary, 1, "COACH", side, None))
        count = poisson(rng, config.shot_count_lambda / 3)
        raw = [
            rng.betavariate(config.chance_beta_a, config.chance_beta_b)
            for _ in range(count)
        ]
        for value in raw:
            timeline.append(
                (
                    start + rng.randint(1, 1799),
                    4,
                    "CHANCE",
                    side,
                    round(
                        clamp(
                            value * result.prematch.expected_xg[side] / 3 / sum(raw),
                            0.006,
                            0.68,
                        ),
                        4,
                    ),
                )
            )
        for _ in range(poisson(rng, config.yellow_lambda / 3)):
            timeline.append((start + rng.randint(1, 1799), 3, "CARD", side, None))
        if rng.random() < config.straight_red_probability_per_team / 3:
            timeline.append((start + rng.randint(1, 1799), 3, "RED", side, None))
    if rng.random() < config.injury_probability_per_match / 3:
        timeline.append(
            (start + rng.randint(1, 1799), 2, "HURT", rng.randrange(2), None)
        )
    for time, priority, kind, side, value in sorted(
        timeline, key=lambda x: (x[0], x[1], x[3] if x[3] is not None else -1)
    ):
        if kind.startswith("EXTRA_TIME"):
            emit(time, kind)
            continue
        if kind == "COACH":
            ensure_keeper(side, time)
            candidates = [p for p in active[side] if players[p].position != "GK"]
            if candidates:
                pid = min(
                    candidates,
                    key=lambda p: (
                        players[p].fitness
                        - stats[p]["seconds"] / 900
                        - stats[p]["yellows"] * 4,
                        p,
                    ),
                )
                substitute(side, pid, time, interval=True)
            continue
        pid = rng.choice(sorted(active[side]))
        if kind in ("CARD", "RED"):
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
            stats[pid]["red"] = True
            leave(side, pid, time)
            emit(
                time,
                "RED_CARD",
                side,
                pid,
                {"reason": "second yellow" if kind == "CARD" else "straight red"},
            )
            if len(active[side]) < 7:
                raise ValueError("ET team below seven; no automatic winner policy")
            ensure_keeper(side, time)
        elif kind == "HURT":
            stats[pid]["injured"] = True
            emit(
                time, "INJURY", side, pid, {"absence_days": config.injury_absence_days}
            )
            if not substitute(side, pid, time):
                leave(side, pid, time)
                emit(time, "PLAYER_OFF_INJURED", side, pid)
                if len(active[side]) < 7:
                    raise ValueError("ET team below seven after injury")
                ensure_keeper(side, time)
        else:
            candidates = sorted(p for p in active[side] if players[p].position != "GK")
            pid = rng.choices(
                candidates,
                weights=[
                    {"DF": 0.45, "MF": 2.5, "FW": 6.1}[players[p].position]
                    * (players[p].attack / 72) ** 2
                    for p in candidates
                ],
            )[0]
            keeper = max(
                active[1 - side],
                key=lambda p: (players[p].position == "GK", players[p].goalkeeping, -p),
            )
            probability = round(
                finishing_probability(value, players[pid], players[keeper], config), 8
            )
            goal = rng.random() < probability
            target = goal or rng.random() < clamp(0.22 + value * 1.03, 0.20, 0.75)
            others = sorted(active[side] - {pid})
            assist = (
                rng.choice(others)
                if goal and rng.random() < config.assist_probability
                else None
            )
            shot = Shot(
                len(shots) + 1,
                time,
                keys[side],
                pid,
                keeper,
                value,
                probability,
                target,
                goal,
                assist,
            )
            shots.append(shot)
            stat = stats[pid]
            stat["shots"] += 1
            stat["on_target"] += int(target)
            stat["goals"] += int(goal)
            stat["xg"] += value
            emit(
                time,
                "SHOT",
                side,
                pid,
                {
                    "shot_id": shot.id,
                    "xg": value,
                    "goal": goal,
                    "on_target": target,
                    "goal_probability": probability,
                    "goalkeeper_id": keeper,
                },
            )
            if goal:
                before = tuple(score)
                score[side] += 1
                if assist is not None:
                    stats[assist]["assists"] += 1
                emit(
                    time,
                    "GOAL",
                    side,
                    pid,
                    {"shot_id": shot.id, "assist_id": assist},
                    before,
                )
            elif target:
                stats[keeper]["saves"] += 1
                emit(time, "SAVE", 1 - side, keeper, {"shot_id": shot.id})
    finish = start + 1800
    for pid, entered_at in entered.items():
        stats[pid]["seconds"] += finish - entered_at
    emit(finish, "EXTRA_TIME_END")
    emit(finish, "FINAL_WHISTLE")
    performances = tuple(
        performance(players[pid], stat, score, rng, config)
        for pid, stat in sorted(stats.items())
    )
    return replace(
        result,
        score=tuple(score),
        events=tuple(events),
        shots=tuple(shots),
        performances=performances,
        duration_seconds=finish,
    )


def resolve(
    snapshot, result, config, rules, prior=(0, 0), *, version=VERSION, equate=True
):
    tied = prior[0] + result.score[0] == prior[1] + result.score[1]
    extended = (
        extra_time(snapshot, result, config, version=version)
        if tied and rules.extra_time
        else result
    )
    played_et = extended is not result
    # Reduce to equal numbers before the shootout, retaining each defending
    # goalkeeper in the eligible taker pool. Excluded outfielders take no kicks.
    if (
        equate
        and rules.penalties
        and prior[0] + extended.score[0] == prior[1] + extended.score[1]
    ):
        last = extended.events[-1]
        ids = [list(last.on_field_home), list(last.on_field_away)]
        size = min(map(len, ids))
        players = {p.id: p for t in (snapshot.home, snapshot.away) for p in t.players}
        if size < 7:
            raise ValueError("Shootout team below seven; adjudication required")
        if len(ids[0]) != len(ids[1]):
            selected = []
            for pool in ids:
                keeper = max(
                    pool,
                    key=lambda p: (
                        players[p].position == "GK",
                        players[p].goalkeeping,
                        -p,
                    ),
                )
                outfield = sorted(
                    (p for p in pool if p != keeper),
                    key=lambda p: (-players[p].composure, -players[p].attack, p),
                )
                selected.append(tuple(sorted([keeper] + outfield[: size - 1])))
            marker = replace(
                last,
                kind="SHOOTOUT_ELIGIBILITY_SET",
                on_field_home=selected[0],
                on_field_away=selected[1],
                details={
                    "excluded": sorted(
                        set(ids[0] + ids[1]) - set(selected[0] + selected[1])
                    ),
                    "policy": "reduce to equate; keep defending goalkeeper",
                },
            )
            final = replace(
                marker, sequence=marker.sequence + 1, kind="FINAL_WHISTLE", details={}
            )
            extended = replace(extended, events=extended.events[:-1] + (marker, final))
    bundle = knockout.resolve(
        snapshot, extended, config, replace(rules, extra_time=False), prior
    )
    bundle["engine_version"] = version
    bundle["regulation"] = asdict(result)
    bundle["resolution"].update(
        version=version,
        rules=asdict(rules),
        extra_time_played=played_et,
        limitations="Proposed ET: six total replacements, one additional live window, interval replacements; five-day modeled injuries; no abandoned-match adjudication",
    )
    return bundle


def validate_bundle(
    snapshot, result, config, rules, prior, bundle, *, version=VERSION, equate=True
):
    checked = validate_match(snapshot, result, config)
    if not checked.ok:
        raise ValueError("Regulation replay failed: " + str(checked.errors))
    if digest(
        resolve(snapshot, result, config, rules, prior, version=version, equate=equate)
    ) != digest(bundle):
        raise ValueError("Forward knockout deterministic replay mismatch")
    # Independent event/shot/stint accounting, in addition to deterministic replay.
    players = {p.id: p for t in (snapshot.home, snapshot.away) for p in t.players}
    active = [set(), set()]
    entered = {}
    seconds = {}
    score = [0, 0]
    last_time = -1
    keys = [snapshot.home.key, snapshot.away.key]
    for i, e in enumerate(bundle["events"], 1):
        if (
            e["sequence"] != i
            or e["elapsed_seconds"] < last_time
            or list(e["pre_score"]) != score
        ):
            raise ValueError("Extension chronology/score mismatch")
        last_time = e["elapsed_seconds"]
        for side, field in enumerate(("on_field_home", "on_field_away")):
            current = set(e[field])
            if (
                len(current) != len(e[field])
                or len(current) > 11
                or any(
                    p not in players or players[p].club_key != keys[side]
                    for p in current
                )
            ):
                raise ValueError("Extension player identity mismatch")
            for pid in current - active[side]:
                entered[pid] = last_time
            for pid in active[side] - current:
                seconds[pid] = seconds.get(pid, 0) + last_time - entered.pop(pid)
            active[side] = current
        if e["kind"] == "GOAL":
            score[keys.index(e["club_key"])] += 1
        if list(e["post_score"]) != score:
            raise ValueError("Shootout changed match score")
    playing_end = result.duration_seconds + (
        1800 if bundle["resolution"]["extra_time_played"] else 0
    )
    for pid, at in entered.items():
        seconds[pid] = seconds.get(pid, 0) + playing_end - at
    if score != bundle["score"] or sum(int(s["goal"]) for s in bundle["shots"]) != sum(
        score
    ):
        raise ValueError("Extension goals do not reconcile")
    for p in bundle["performances"]:
        if p["seconds_played"] != seconds.get(p["player_id"], 0) or p["goals"] != sum(
            s["goal"] for s in bundle["shots"] if s["player_id"] == p["player_id"]
        ):
            raise ValueError("Extension stint/player accounting mismatch")
    return {
        "ok": True,
        "regulation_checks": checked.checks,
        "extension_replayed": True,
        "independent_extension_accounting": True,
    }
