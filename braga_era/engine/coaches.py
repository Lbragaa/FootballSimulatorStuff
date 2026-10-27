"""Autonomous, form/fitness/role-aware decisions with bounded imperfect judgement."""

from .models import MatchPlan
from .randomness import stream, verify_commitment


class SelectionError(ValueError):
    pass


def eligible(player, snapshot):
    return (
        player.eligible
        and not player.exclusion_reasons
        and player.id not in snapshot.archived_ids
        and player.fitness > 0
    )


def prepare(snapshot, config, seeds):
    config.validate()
    verify_commitment(snapshot, config, seeds)
    plans = []
    for team, opponent in (
        (snapshot.home, snapshot.away),
        (snapshot.away, snapshot.home),
    ):
        rng = stream(seeds, "coach:" + team.key)
        pool = [p for p in team.players if eligible(p, snapshot)]
        if len(pool) < 11:
            raise SelectionError(
                f"{team.name}: only {len(pool)} eligible recorded players; missing squads cannot be invented"
            )
        roles = (
            ("GK", "GK"),
            ("RB", "DF"),
            ("CB1", "DF"),
            ("CB2", "DF"),
            ("LB", "DF"),
            ("DM1", "MF"),
            ("DM2", "MF"),
            ("AM", "MF"),
            ("RW", "FW"),
            ("LW", "FW"),
            ("ST", "FW"),
        )
        if team.coach.formation == "4-3-3":
            roles = roles[:5] + (("DM", "MF"), ("CM1", "MF"), ("CM2", "MF")) + roles[8:]
        chosen = []
        assignments = []
        # Score each player's current attributes once; never look at outcomes.
        scores = {
            p.id: p.ovr
            + getattr(config, "lineup_fitness_weight", 0.05) * p.fitness
            + 0.01 * p.morale
            + config.lineup_form_weight * (p.form - 6.55)
            + team.coach.continuity_preference * min(1, len(p.recent_ratings) / 4)
            + max(-2, min(2, rng.gauss(0, team.coach.decision_noise)))
            for p in pool
        }
        for role, position in roles:
            candidates = [
                p for p in pool if p.id not in chosen and p.position == position
            ]
            if not candidates and role != "GK":
                candidates = [
                    p for p in pool if p.id not in chosen and p.position != "GK"
                ]
            if not candidates:
                raise SelectionError(
                    f"{team.name}: no eligible recorded {role} available"
                )

            def score(p):
                suitability = 0 if p.position == position else -8
                if role.startswith("CB"):
                    suitability += (p.defense - 72) * 0.10
                elif role.startswith("DM"):
                    suitability += (p.defense + p.passing - 144) * 0.035
                elif role == "AM":
                    suitability += (p.passing - 72) * 0.12
                elif role in ("ST", "RW", "LW"):
                    suitability += (p.attack - 72) * 0.08
                return scores[p.id] + suitability

            player = max(candidates, key=lambda p: (score(p), -p.id))
            chosen.append(player.id)
            assignments.append((player.id, role))
        bench = sorted(
            (p for p in pool if p.id not in chosen), key=lambda p: (-scores[p.id], p.id)
        )[:12]
        # Tactical choice is imperfect and reacts to relative quality, not club name.
        inclination = (
            team.coach.risk_preference
            + (team.strength - opponent.strength) * 0.02
            + max(-0.4, min(0.4, rng.gauss(0, 0.16)))
        )
        risk = (
            "attacking"
            if inclination > 0.64
            else "cautious" if inclination < 0.36 else "balanced"
        )
        windows = tuple(max(46, min(88, m + rng.randint(-3, 3))) for m in (59, 73, 82))
        plans.append(
            MatchPlan(
                team.key,
                team.coach.name,
                team.coach.formation,
                team.coach.defensive_shape,
                risk,
                tuple(chosen),
                tuple(p.id for p in bench),
                tuple(assignments),
                windows,
                (
                    "Selected by recorded IDs, eligibility, positional fit, OVR, fitness, morale, rolling form and continuity",
                    f"Risk {risk}: coach preference, opponent strength and bounded imperfect judgement",
                    "No guaranteed starter names; no user-mandated changes or outcome-dependent rerolls",
                ),
            )
        )
    return tuple(plans)
