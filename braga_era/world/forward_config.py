"""Registered forward configurations; original regulation defaults stay immutable."""

from dataclasses import asdict, dataclass
from ..engine import EngineConfig
from ..engine.substitutions import VERSION as STINT_AWARE_VERSION
from ..engine.config import REALISM_VERSION
from .policy import is_readiness, ReadinessPolicy


@dataclass(frozen=True)
class ForwardConfig(EngineConfig):
    version: str = "braga-headless-1.1.0"
    lineup_fitness_weight: float = 0.12
    neutral_final: bool = False


def configuration(policy, final=False, *, engine_version=None):
    if is_readiness(policy):
        if engine_version not in (None, STINT_AWARE_VERSION, REALISM_VERSION):
            raise ValueError("Unsupported forward engine version")
        return ForwardConfig(
            version=engine_version or ForwardConfig.version,
            home_base_xg=1.375 if final else 1.55,
            away_base_xg=1.375 if final else 1.20,
            neutral_final=final,
            **({"yellow_lambda": 2.55, "maximum_yellow_events_per_team": 8,
                "club_quality_weight": 0.64, "xi_quality_weight": 0.36,
                "quality_difference_xg": 0.042,
                "goalkeeper_probability_weight": 0.004,
                "composure_probability_weight": 0.0025,
                "finishing_attack_weight": 0.0015}
               if engine_version == REALISM_VERSION else {}),
        )
    if engine_version is not None:
        raise ValueError("Stint-aware configuration requires a readiness policy")
    return EngineConfig()


def load(value, policy, final=False):
    engine_version = (
        value["version"]
        if isinstance(value, dict) and value.get("version") in (STINT_AWARE_VERSION, REALISM_VERSION)
        else None
    )
    expected = configuration(policy, final, engine_version=engine_version)
    if value != asdict(expected):
        raise ValueError("Unsupported engine/config version")
    return expected
