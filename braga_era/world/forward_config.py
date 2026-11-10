"""Registered forward configurations; original regulation defaults stay immutable."""

from dataclasses import asdict, dataclass
from ..engine import EngineConfig
from ..engine.substitutions import VERSION as STINT_AWARE_VERSION
from .policy import is_readiness, ReadinessPolicy


@dataclass(frozen=True)
class ForwardConfig(EngineConfig):
    version: str = "braga-headless-1.1.0"
    lineup_fitness_weight: float = 0.12
    neutral_final: bool = False


def configuration(policy, final=False, *, engine_version=None):
    if is_readiness(policy):
        if engine_version not in (None, STINT_AWARE_VERSION):
            raise ValueError("Unsupported forward engine version")
        return ForwardConfig(
            version=engine_version or ForwardConfig.version,
            home_base_xg=1.375 if final else 1.55,
            away_base_xg=1.375 if final else 1.20,
            neutral_final=final,
        )
    if engine_version is not None:
        raise ValueError("Stint-aware configuration requires a readiness policy")
    return EngineConfig()


def load(value, policy, final=False):
    engine_version = (
        STINT_AWARE_VERSION
        if isinstance(value, dict) and value.get("version") == STINT_AWARE_VERSION
        else None
    )
    expected = configuration(policy, final, engine_version=engine_version)
    if value != asdict(expected):
        raise ValueError("Unsupported engine/config version")
    return expected
