"""Registered forward configurations; original regulation defaults stay immutable."""

from dataclasses import asdict, dataclass
from ..engine import EngineConfig
from .policy import is_readiness, ReadinessPolicy


@dataclass(frozen=True)
class ForwardConfig(EngineConfig):
    version: str = "braga-headless-1.1.0"
    lineup_fitness_weight: float = 0.12
    neutral_final: bool = False


def configuration(policy, final=False):
    if is_readiness(policy):
        return ForwardConfig(
            home_base_xg=1.375 if final else 1.55,
            away_base_xg=1.375 if final else 1.20,
            neutral_final=final,
        )
    return EngineConfig()


def load(value, policy, final=False):
    expected = configuration(policy, final)
    if value != asdict(expected):
        raise ValueError("Unsupported engine/config version")
    return expected
