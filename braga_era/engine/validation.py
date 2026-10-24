"""Independent chronological replay and accounting audits; no state persistence."""

from dataclasses import dataclass
from math import isfinite

from .models import SCOPE
from .coaches import eligible


@dataclass(frozen=True)
class Validation:
    errors: tuple[str, ...]
    checks: int

    @property
    def ok(self):
        return not self.errors

    def to_dict(self):
        return {
            "ok": self.ok,
            "checks": self.checks,
            "failures": len(self.errors),
            "errors": list(self.errors),
        }


def validate_plans(snapshot, plans):
    issues = []
    all_ids = [p.id for t in (snapshot.home, snapshot.away) for p in t.players]
    if len(all_ids) != len(set(all_ids)):
        issues.append("Player ID occurs in both squads or is duplicated")
    if snapshot.home.key == snapshot.away.key:
        issues.append("Home and away identities are the same")
    if len(plans) != 2:
        return issues + ["Exactly two team plans required"]
    for team, plan in zip((snapshot.home, snapshot.away), plans):
        players = {p.id: p for p in team.players}
        if any(p.club_key != team.key for p in team.players):
            issues.append("Player membership differs from stable team identity")
        if any(p.position not in ("GK", "DF", "MF", "FW") for p in team.players):
            issues.append("Unknown player position")
        if plan.club_key != team.key:
            issues.append("Plan/team identity differs")
        if len(plan.starters) != 11 or len(set(plan.starters)) != 11:
            issues.append("Exactly 11 unique starters required per team")
        chosen = list(plan.starters) + list(plan.bench)
        if len(set(chosen)) != len(chosen):
            issues.append("Starter/bench identities overlap or repeat")
        if any(
            pid not in players or not eligible(players[pid], snapshot) for pid in chosen
        ):
            issues.append("Ineligible or unknown selected player")
        if not any(
            pid in players and players[pid].position == "GK" for pid in plan.starters
        ):
            issues.append("No starting goalkeeper")
        if plan.risk not in ("balanced", "attacking", "cautious"):
            issues.append("Unknown tactical risk")
        if tuple(pid for pid, _ in plan.roles) != plan.starters:
            issues.append("Role assignment differs from starting XI")
        if any(not 46 <= m <= 88 for m in plan.substitution_minutes):
            issues.append("Coach substitution window outside allowed range")
    return issues


def validate_match(snapshot, result, config=None):
    from .config import EngineConfig
    from .randomness import verify_commitment

    cfg = config or EngineConfig()
    errors = list(validate_plans(snapshot, result.plans))
    checks = 0

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    check(
        snapshot.scope == result.scope == SCOPE,
        "Official execution is not supported by this engine interface",
    )
    check(result.fixture_key == snapshot.fixture_key, "Fixture identity differs")
    check(result.snapshot_sha256 == snapshot.fingerprint, "Input snapshot hash differs")
    check(
        result.config_sha256 == cfg.fingerprint
        and result.engine_version == cfg.version,
        "Engine/configuration identity differs",
    )
    try:
        verify_commitment(snapshot, cfg, result.seeds)
    except ValueError:
        errors.append("Committed seed/input/configuration mismatch")
    if errors:
        return Validation(tuple(errors), checks)
    teams = (snapshot.home, snapshot.away)
    keys = [t.key for t in teams]
    players = {p.id: p for team in teams for p in team.players}
    active = [set(p.starters) for p in result.plans]
    benches = [set(p.bench) for p in result.plans]
    score = [0, 0]
    subs = [0, 0]
    windows = [set(), set()]
    injured = set()
    red = set()
    yellows = {}
    entry = {}
    seconds = {}
    counts = {
        p: {"goals": 0, "assists": 0, "shots": 0, "on_target": 0, "xg": 0.0, "saves": 0}
        for plan in result.plans
        for p in plan.starters
    }
    for plan in result.plans:
        for pid in plan.starters:
            entry[pid] = 0
            seconds[pid] = 0
    shot_map = {s.id: s for s in result.shots}
    seen_shots = set()
    goals = set()
    saved = set()
    check(
        len(shot_map) == len(result.shots)
        and set(shot_map) == set(range(1, len(result.shots) + 1)),
        "Shot IDs duplicate or are not contiguous",
    )
    check(
        [e.sequence for e in result.events] == list(range(1, len(result.events) + 1)),
        "Event sequence is not stable/contiguous",
    )
    check(
        all(
            a.elapsed_seconds <= b.elapsed_seconds
            for a, b in zip(result.events, result.events[1:])
        ),
        "Events are not chronological",
    )
    check(
        bool(result.events)
        and result.events[0].kind == "KICKOFF"
        and result.events[-1].kind == "FINAL_WHISTLE",
        "Period start/final whistle missing",
    )
    boundaries = [
        e.kind
        for e in result.events
        if e.kind in ("KICKOFF", "HALF_TIME", "SECOND_HALF_KICKOFF", "FINAL_WHISTLE")
    ]
    check(
        boundaries == ["KICKOFF", "HALF_TIME", "SECOND_HALF_KICKOFF", "FINAL_WHISTLE"],
        "Period boundaries missing, duplicated or out of order",
    )
    for e in result.events:
        if e.kind in ("KICKOFF", "HALF_TIME", "SECOND_HALF_KICKOFF", "FINAL_WHISTLE"):
            check(
                e.elapsed_seconds
                == {
                    "KICKOFF": 0,
                    "HALF_TIME": 2700,
                    "SECOND_HALF_KICKOFF": 2700,
                    "FINAL_WHISTLE": result.duration_seconds,
                }[e.kind],
                "Period boundary clock differs",
            )
    check(
        result.duration_seconds == (90 + cfg.stoppage_minutes) * 60,
        "Duration differs from committed rules",
    )

    def close(pid, time):
        if pid not in entry:
            errors.append("Exit without active entry")
            return
        seconds[pid] += time - entry.pop(pid)

    for e in result.events:
        check(
            0 <= e.elapsed_seconds <= result.duration_seconds,
            "Event outside regulation/stoppage clock",
        )
        check(
            e.period
            == ("1" if e.elapsed_seconds < 2700 or e.kind == "HALF_TIME" else "2"),
            "Event period differs from match clock",
        )
        check(e.pre_score == tuple(score), "Event pre-score is inconsistent")
        side = keys.index(e.club_key) if e.club_key in keys else None
        pid = e.player_id
        try:
            if e.kind == "SUBSTITUTION":
                old = e.details["outgoing_id"]
                if (
                    side is None
                    or old not in active[side]
                    or pid not in benches[side]
                    or pid in counts
                ):
                    errors.append("Illegal substitution or player reentry")
                    continue
                active[side].remove(old)
                close(old, e.elapsed_seconds)
                active[side].add(pid)
                benches[side].remove(pid)
                entry[pid] = e.elapsed_seconds
                seconds[pid] = 0
                counts[pid] = {
                    "goals": 0,
                    "assists": 0,
                    "shots": 0,
                    "on_target": 0,
                    "xg": 0.0,
                    "saves": 0,
                }
                subs[side] += 1
                windows[side].add(e.elapsed_seconds)
            elif e.kind in (
                "YELLOW_CARD",
                "RED_CARD",
                "INJURY",
                "WITHDRAWAL",
                "SHOT",
                "GOAL",
                "SAVE",
            ):
                if side is None or pid not in active[side]:
                    errors.append("Event actor not on field for that club")
                    continue
                if pid in injured and e.kind != "WITHDRAWAL":
                    errors.append("Injured player acts after injury")
                if e.kind == "YELLOW_CARD":
                    yellows[pid] = yellows.get(pid, 0) + 1
                    check(
                        e.details.get("yellow_count") == yellows[pid],
                        "Yellow-card count differs",
                    )
                elif e.kind == "RED_CARD":
                    if (
                        e.details.get("reason") == "second yellow"
                        and yellows.get(pid, 0) != 2
                    ):
                        errors.append("Second-yellow red without two yellows")
                    red.add(pid)
                    active[side].remove(pid)
                    close(pid, e.elapsed_seconds)
                elif e.kind == "INJURY":
                    injured.add(pid)
                elif e.kind == "WITHDRAWAL":
                    if pid not in injured:
                        errors.append("Withdrawal without recorded injury")
                    active[side].remove(pid)
                    close(pid, e.elapsed_seconds)
                elif e.kind == "SHOT":
                    shot = shot_map[e.details["shot_id"]]
                    check(shot.id not in seen_shots, "Shot event duplicated")
                    seen_shots.add(shot.id)
                    check(
                        (shot.player_id, shot.club_key, shot.elapsed_seconds)
                        == (pid, e.club_key, e.elapsed_seconds),
                        "Shot attribution/clock differs",
                    )
                    check(
                        shot.goalkeeper_id in active[1 - side]
                        and shot.goalkeeper_id not in injured,
                        "Goalkeeper not eligible/on field",
                    )
                    check(
                        0 < shot.xg <= 1 and 0 < shot.goal_probability < 1,
                        "Invalid chance/probability",
                    )
                    check(not shot.goal or shot.on_target, "Goal is not on target")
                    check(
                        e.details.get("xg") == shot.xg
                        and e.details.get("goal") == shot.goal
                        and e.details.get("on_target") == shot.on_target,
                        "Shot event/report differs",
                    )
                    counts[pid]["shots"] += 1
                    counts[pid]["on_target"] += int(shot.on_target)
                    counts[pid]["xg"] += shot.xg
                elif e.kind == "GOAL":
                    shot = shot_map[e.details["shot_id"]]
                    check(
                        shot.id in seen_shots and shot.goal and shot.id not in goals,
                        "Goal lacks one unique scored shot",
                    )
                    check(
                        shot.player_id == pid and shot.club_key == e.club_key,
                        "Goal scorer/team differs from shot",
                    )
                    goals.add(shot.id)
                    score[side] += 1
                    counts[pid]["goals"] += 1
                    assist = e.details.get("assist_id")
                    check(
                        assist == shot.assist_id,
                        "Assist differs from scored-shot record",
                    )
                    if assist is not None:
                        if (
                            assist == pid
                            or assist not in active[side]
                            or assist in injured
                        ):
                            errors.append(
                                "Assist actor is not an eligible on-field teammate"
                            )
                        else:
                            counts[assist]["assists"] += 1
                elif e.kind == "SAVE":
                    shot = shot_map[e.details["shot_id"]]
                    check(
                        shot.id in seen_shots
                        and shot.on_target
                        and not shot.goal
                        and shot.id not in saved,
                        "Invalid or duplicate save",
                    )
                    check(
                        shot.goalkeeper_id == pid,
                        "Save actor differs from shot goalkeeper",
                    )
                    saved.add(shot.id)
                    counts[pid]["saves"] += 1
            elif e.kind not in (
                "KICKOFF",
                "HALF_TIME",
                "SECOND_HALF_KICKOFF",
                "FINAL_WHISTLE",
                "TACTICAL_CHANGE",
            ):
                errors.append("Unknown event type")
            check(e.post_score == tuple(score), "Event post-score is inconsistent")
            check(
                e.on_field_home == tuple(sorted(active[0]))
                and e.on_field_away == tuple(sorted(active[1])),
                "Stored on-field state differs from replay",
            )
            check(
                all(7 <= len(a) <= 11 for a in active),
                "On-field team size outside legal bounds",
            )
        except (KeyError, TypeError, ValueError):
            errors.append("Malformed event or unknown actor/shot")
    for side in (0, 1):
        for pid in active[side]:
            close(pid, result.duration_seconds)
    check(
        subs[0] <= cfg.maximum_substitutions and subs[1] <= cfg.maximum_substitutions,
        "Too many substitutions",
    )
    check(
        all(len(w) <= cfg.maximum_substitution_windows for w in windows),
        "Too many substitution stoppages",
    )
    check(seen_shots == set(shot_map), "Missing shot event")
    check(
        goals == {s.id for s in result.shots if s.goal},
        "Scored shots do not match goal events",
    )
    check(
        saved == {s.id for s in result.shots if s.on_target and not s.goal},
        "Saved-shot accounting differs",
    )
    check(tuple(score) == result.score, "Final score differs from replay")
    performances = {p.player_id: p for p in result.performances}
    check(
        len(performances) == len(result.performances)
        and set(performances) == set(counts),
        "Participation rows duplicate or omit players",
    )
    for pid, p in performances.items():
        if pid not in counts or pid not in players:
            continue
        row = counts[pid]
        source = players[pid]
        check(
            p.seconds_played == seconds[pid]
            and 0 <= p.seconds_played <= result.duration_seconds,
            "Participation duration differs from replay",
        )
        check(
            p.club_key in keys
            and p.club_key == source.club_key
            and p.starter == (pid in result.plans[keys.index(p.club_key)].starters),
            "Participation team/starter differs",
        )
        check(
            (p.goals, p.assists, p.shots, p.on_target, p.saves)
            == tuple(
                row[k] for k in ("goals", "assists", "shots", "on_target", "saves")
            ),
            "Player goals/assists/shots/saves differ",
        )
        check(abs(p.xg - round(row["xg"], 4)) < 0.00001, "Player xG does not reconcile")
        check(
            (p.yellows, p.red, p.injured)
            == (yellows.get(pid, 0), pid in red, pid in injured),
            "Player cards/injury differ",
        )
        check(
            (p.fitness_before, p.morale_before, p.form_before)
            == (source.fitness, source.morale, source.form),
            "Invented pregame player state",
        )
        check(
            0 <= p.fitness_after <= p.fitness_before
            and 0 <= p.morale_after <= 100
            and 5.2 <= p.rating <= 9.8
            and isfinite(p.form_after),
            "Invalid postmatch fitness/morale/rating/form",
        )
    check(0 <= result.possession_home <= 100, "Invalid possession")
    p = result.prematch
    check(
        all(
            0 <= v <= 1
            for v in (
                p.home_win_probability,
                p.draw_probability,
                p.away_win_probability,
            )
        )
        and abs(
            p.home_win_probability + p.draw_probability + p.away_win_probability - 1
        )
        < 1e-8,
        "Invalid prematch probabilities",
    )
    return Validation(tuple(errors), checks)
