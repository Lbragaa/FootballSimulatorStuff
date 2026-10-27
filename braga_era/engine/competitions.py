"""Contracts for Task 03B adapters. No official runner or persistence implementation."""

from dataclasses import dataclass
from typing import Protocol

from .models import CompetitionRules, MatchResult, Snapshot


@dataclass(frozen=True)
class CalendarEntry:
    fixture_key: str
    kickoff: str
    competition: str
    season: int
    confirmed_participants: bool


@dataclass(frozen=True)
class Progression:
    """Adapter output, never inferred by the regulation match engine."""

    aggregate: tuple[int, int] | None
    qualified_club_key: str | None
    requires_extra_time: bool
    requires_penalties: bool
    next_fixture_keys: tuple[str, ...]


class CompetitionAdapter(Protocol):
    def due_entries(self, as_of: str) -> tuple[CalendarEntry, ...]: ...
    def rules_for(self, fixture_key: str) -> CompetitionRules: ...
    def pregame(self, fixture_key: str) -> Snapshot: ...
    def progression(self, result: MatchResult) -> Progression: ...


class PlayerStateProvider(Protocol):
    """One cross-competition timeline; implementations must not recover per round."""

    def at_kickoff(self, club_key: str, kickoff: str) -> tuple: ...
    def proposed_deltas(self, result: MatchResult) -> tuple: ...


def ordered_agenda(entries):
    """Pure global chronological ordering of ISO-local fictional calendar entries."""
    entries = tuple(entries)
    if len({e.fixture_key for e in entries}) != len(entries):
        raise ValueError("Duplicate global fixture identity")
    return tuple(sorted(entries, key=lambda e: (e.kickoff, e.fixture_key)))
