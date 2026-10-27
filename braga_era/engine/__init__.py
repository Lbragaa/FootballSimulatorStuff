"""Headless noncanonical match simulation. No official persistence API."""

from .config import EngineConfig
from .randomness import commit_seeds
from .coaches import prepare
from .match import simulate_match
from .validation import validate_match

__all__ = [
    "EngineConfig",
    "commit_seeds",
    "prepare",
    "simulate_match",
    "validate_match",
]
