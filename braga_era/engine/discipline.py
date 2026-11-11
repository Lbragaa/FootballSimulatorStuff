"""Shared recipient weights for the version 1.3 disciplinary model."""

POSITION_EXPOSURE = {"GK": 0.30, "DF": 1.35, "MF": 1.20, "FW": 0.80}
SECOND_CAUTION_WEIGHT = 0.16


def recipient(rng, active, players, statistics, *, caution):
    ordered = sorted(active)
    weights = []
    for player_id in ordered:
        player = players[player_id]
        composure = max(0.85, min(1.15, 1 + (70 - player.composure) * 0.005))
        weight = POSITION_EXPOSURE[player.position] * composure
        if caution and statistics[player_id]["yellows"]:
            weight *= SECOND_CAUTION_WEIGHT
        weights.append(weight)
    return rng.choices(ordered, weights=weights)[0]


def short_handed_xg(own_count, opposing_count, config):
    """Use the same live player-count effect in regulation and extra time."""
    return max(0.45, 1 - config.missing_player_xg_penalty * (11 - own_count)) * (
        1 + 0.075 * (11 - opposing_count))
