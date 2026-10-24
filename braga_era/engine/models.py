"""Immutable snapshots and typed match contracts; no database dependencies."""

from dataclasses import asdict, dataclass, field
from typing import Any

from ..history import digest

SCOPE = "NONCANONICAL TEST SIMULATION"


@dataclass(frozen=True)
class Player:
    id: int
    club_key: str
    name: str
    position: str
    ovr: float
    attack: float
    defense: float
    passing: float
    physical: float
    composure: float
    goalkeeping: float
    fitness: float
    morale: float
    form: float = 6.55
    eligible: bool = True
    exclusion_reasons: tuple[str, ...] = ()
    recent_ratings: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class Coach:
    name: str = "Autonomous club coach"
    formation: str = "4-3-3"
    defensive_shape: str = "4-4-2"
    risk_preference: float = 0.5
    continuity_preference: float = 0.4
    decision_noise: float = 0.8


@dataclass(frozen=True)
class Team:
    key: str
    name: str
    strength: float
    form: float
    players: tuple[Player, ...]
    coach: Coach = field(default_factory=Coach)


@dataclass(frozen=True)
class CompetitionRules:
    competition: str
    season: int = 2027
    aggregate_before: tuple[int, int] | None = None
    extra_time_if_tied: bool = False
    penalties_if_tied: bool = False
    away_goals: bool = False
    progression: str = "No qualification or official progression in Phase 2A"


@dataclass(frozen=True)
class Snapshot:
    fixture_key: str
    kickoff: str
    as_of: str
    home: Team
    away: Team
    rules: CompetitionRules
    source_sha256: str
    archived_ids: tuple[int, ...] = (196,)
    synthetic: bool = False
    notes: tuple[str, ...] = ()
    scope: str = SCOPE

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class MatchPlan:
    club_key: str
    coach: str
    formation: str
    defensive_shape: str
    risk: str
    starters: tuple[int, ...]
    bench: tuple[int, ...]
    roles: tuple[tuple[int, str], ...]
    substitution_minutes: tuple[int, ...]
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class SeedCommitment:
    root_sha256: str
    snapshot_sha256: str
    config_sha256: str
    requested_seed: str
    namespace: str = "noncanonical-sandbox"
    algorithm: str = "sha256-named-streams/python-random-MT19937-v1"


@dataclass(frozen=True)
class Prematch:
    home_quality: float
    away_quality: float
    expected_xg: tuple[float, float]
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    method: str = (
        "Independent Poisson goal approximation from pregame xG; not a guaranteed outcome"
    )


@dataclass(frozen=True)
class Event:
    sequence: int
    elapsed_seconds: int
    period: str
    kind: str
    club_key: str | None
    player_id: int | None
    pre_score: tuple[int, int]
    post_score: tuple[int, int]
    on_field_home: tuple[int, ...]
    on_field_away: tuple[int, ...]
    details: dict[str, Any]


@dataclass(frozen=True)
class Shot:
    id: int
    elapsed_seconds: int
    club_key: str
    player_id: int
    goalkeeper_id: int
    xg: float
    goal_probability: float
    on_target: bool
    goal: bool
    assist_id: int | None


@dataclass(frozen=True)
class Performance:
    player_id: int
    club_key: str
    starter: bool
    seconds_played: int
    goals: int
    assists: int
    shots: int
    on_target: int
    xg: float
    saves: int
    yellows: int
    red: bool
    injured: bool
    rating: float
    fitness_before: float
    fitness_after: float
    morale_before: float
    morale_after: float
    form_before: float
    form_after: float


@dataclass(frozen=True)
class MatchResult:
    fixture_key: str
    snapshot_sha256: str
    config_sha256: str
    engine_version: str
    seeds: SeedCommitment
    plans: tuple[MatchPlan, MatchPlan]
    prematch: Prematch
    score: tuple[int, int]
    possession_home: float
    events: tuple[Event, ...]
    shots: tuple[Shot, ...]
    performances: tuple[Performance, ...]
    duration_seconds: int
    scope: str = SCOPE

    @property
    def fingerprint(self):
        return digest(asdict(self))
