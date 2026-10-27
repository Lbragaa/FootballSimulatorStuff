"""Versioned proposals. No policy in this module is canonically approved."""

from dataclasses import asdict, dataclass
from ..history import digest


@dataclass(frozen=True)
class WorldPolicy:
    version: str = "world-proposals-1.0.0"
    roster_version: str = "fictional-squads-1.0.0"
    roster_seed: str = "task03b-fictional-rosters-v1"
    recovery_per_day: float = 1.5
    yellow_threshold: int = 3
    red_suspension_matches: int = 1
    unknown_historical_bans: str = (
        "unknown; forward counters start at zero, never a historical assertion"
    )
    registration_prior: str = (
        "current recorded club membership except archived identities; honor known signing contract dates"
    )
    cup_tie_policy: str = (
        "proposal: no away goals; two-leg ties direct penalties; single finals 30m extra time then penalties"
    )
    draw_policy: str = (
        "unresolved continental draws remain conditional; CDB follows recorded next_tie"
    )
    canonical_approval: bool = False

    @property
    def fingerprint(self):
        return digest(asdict(self))

    def validate(self):
        if self != WorldPolicy():
            raise ValueError(
                "Unsupported world policy/version; register a reviewed forward policy instead of silently changing parameters"
            )


@dataclass(frozen=True)
class Rules:
    competition: str
    version: str = "knockout-proposal-1.0.0"
    away_goals: bool = False
    extra_time: bool = False
    penalties: bool = False
    proposal: bool = True


def rules_for(competition, decisive=False, single_final=False):
    if competition not in ("LEAGUE", "CDB", "LIB", "SULA"):
        raise ValueError("Unsupported competition")
    return Rules(
        competition,
        extra_time=bool(decisive and single_final),
        penalties=bool(decisive),
    )
