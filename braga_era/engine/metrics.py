"""Legacy-derived postmatch metrics shared by regulation and forward extensions."""

from math import sqrt
from .models import Performance


def performance(p, stat, score, rng, config):
    side = stat["side"]
    win = score[side] > score[1 - side]
    loss = score[side] < score[1 - side]
    rating = round(
        max(
            5.2,
            min(
                9.8,
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
            ),
        ),
        1,
    )
    fatigue = rng.uniform(config.fitness_loss_min, config.fitness_loss_max) * (
        stat["seconds"] / 5400
    )
    if stat["injured"]:
        fatigue += 5
    recent = [(rating, stat["seconds"] / 60)] + list(p.recent_ratings[:3])
    weights = [0.68**i * sqrt(min(1, m / 60)) for i, (_, m) in enumerate(recent)]
    newform = 6.55 + (
        sum(w * r for w, (r, _) in zip(weights, recent)) / sum(weights) - 6.55
    ) * min(1, len(recent) / 3)
    return Performance(
        p.id,
        p.club_key,
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
        round(max(0, min(100, p.fitness - fatigue)), 2),
        p.morale,
        max(0, min(100, p.morale + (2 if win else -2 if loss else 0))),
        p.form,
        round(newform, 3),
    )
