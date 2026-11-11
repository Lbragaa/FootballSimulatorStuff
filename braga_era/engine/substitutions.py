"""Versioned tactical substitution estimates using only information at the window."""

from collections import Counter
from .config import REALISM_VERSION


VERSION = "braga-headless-1.2.0"

STINT_AWARE_VERSIONS = (VERSION, REALISM_VERSION)
TACTICAL_REASON = "score-aware positional refresh"


def choose_tactical(players, bench, roles, seconds, stats, goal_difference, refreshed, rng, noise):
    """Return a worthwhile same-position change, or leave the team as it is."""
    if goal_difference < 0:
        priority = {"FW": 1.6, "MF": 0.7, "DF": 0.0}
    elif goal_difference > 0:
        priority = {"FW": 0.0, "MF": 0.8, "DF": 1.2}
    else:
        priority = {"FW": 0.4, "MF": 0.6, "DF": 0.4}
    candidates = []
    for outgoing, played in sorted(seconds.items()):
        stat = stats[outgoing]
        player = players[outgoing]
        position = player.position
        if not stat["starter"] or stat["injured"] or stat["red"] or position == "GK":
            continue
        role = roles[outgoing]
        # Project current freshness from the checkpoint and this match's actual
        # stint. Preserve contributions and account for the risk of another card.
        workload = played / 60 * 0.17
        impact = 3.0 * stat["goals"] + 1.8 * stat["assists"] - 3.0 * stat["yellows"]
        current = suitability(player, role, goal_difference) - 0.52 * workload + impact
        for incoming in sorted(bench):
            replacement = players[incoming]
            if replacement.position != position:
                continue
            gain = suitability(replacement, role, goal_difference) - current
            gain += priority[position] - 3.0 * refreshed.get(position, 0)
            if gain >= 3.5:
                # Variety decides between defensible changes. Noise alone
                # cannot turn an unsuitable replacement into a candidate.
                judgement = max(-1.5, min(1.5, rng.gauss(0, noise)))
                candidates.append((gain + judgement, -outgoing, -incoming))
    if not candidates:
        return None
    _, outgoing, incoming = max(candidates)
    return -outgoing, -incoming


def suitability(player, role, goal_difference):
    if role.startswith(("CB", "DM")) or goal_difference > 0 and player.position == "DF":
        skill = player.defense
    elif role in ("ST", "RW", "LW") or goal_difference < 0 and player.position == "FW":
        skill = player.attack
    else:
        skill = player.passing
    return (0.75 * player.ovr + 0.25 * skill + 1.5 * (player.form - 6.55)
            + 0.52 * (player.fitness - 85) + 0.02 * (player.morale - 50))


def previous_refreshes(events, club, players):
    return Counter(players[event.player_id].position for event in events
                   if event.kind == "SUBSTITUTION" and event.club_key == club
                   and event.details["reason"] == TACTICAL_REASON)
