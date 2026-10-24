"""Explicit legacy-derived starting values and documented forward extensions."""

from dataclasses import asdict, dataclass
from math import isfinite

from ..history import digest


@dataclass(frozen=True)
class EngineConfig:
    version: str = "braga-headless-1.0.0"
    club_quality_weight: float = 0.71
    xi_quality_weight: float = 0.29
    team_form_weight: float = 0.42
    individual_form_weight: float = 0.45
    fitness_quality_weight: float = 0.02
    home_base_xg: float = 1.55
    away_base_xg: float = 1.20
    quality_difference_xg: float = 0.054
    shot_count_lambda: float = 11
    shot_strength_coefficient: float = 0.08
    shot_minimum: int = 5
    shot_maximum: int = 21
    chance_beta_a: float = 1.5
    chance_beta_b: float = 12
    finishing_form_weight: float = 0.25
    lineup_form_weight: float = 2.1
    goalkeeper_probability_weight: float = 0.006
    composure_probability_weight: float = 0.003
    finishing_attack_weight: float = 0.002
    assist_probability: float = 0.72
    yellow_lambda: float = 1.55
    maximum_yellow_events_per_team: int = 4
    straight_red_probability_per_team: float = 0.035
    injury_probability_per_match: float = 0.015
    injury_absence_days: int = 5
    fitness_loss_min: float = 3
    fitness_loss_max: float = 8
    maximum_substitutions: int = 5
    maximum_substitution_windows: int = 3
    stoppage_minutes: int = 3
    live_attack_xg_multiplier: float = 1.08
    live_caution_xg_multiplier: float = 0.94
    missing_player_xg_penalty: float = 0.10
    isolated_rng_streams: bool = True

    @property
    def fingerprint(self):
        return digest(asdict(self))

    def validate(self):
        if any(
            isinstance(value, (int, float)) and not isfinite(value)
            for value in asdict(self).values()
        ):
            raise ValueError("Engine parameters must be finite")
        if (
            self.shot_minimum < 1
            or self.shot_maximum < self.shot_minimum
            or self.shot_maximum > 100
            or self.shot_count_lambda > 100
            or self.yellow_lambda > 100
            or self.maximum_substitutions not in range(0, 6)
            or self.maximum_substitution_windows not in range(0, 4)
            or not 0 <= self.maximum_yellow_events_per_team <= 4
            or not 0 <= self.stoppage_minutes <= 10
            or self.chance_beta_a <= 0
            or self.chance_beta_b <= 0
            or self.shot_count_lambda <= 0
            or self.yellow_lambda < 0
            or self.fitness_loss_min < 0
            or self.fitness_loss_max < self.fitness_loss_min
        ):
            raise ValueError("Invalid engine configuration")
        for probability in (
            self.assist_probability,
            self.straight_red_probability_per_team,
            self.injury_probability_per_match,
        ):
            if not 0 <= probability <= 1:
                raise ValueError("Invalid event probability")
        if not self.isolated_rng_streams:
            raise ValueError("Named RNG streams are required in this engine version")


PARAMETER_PROVENANCE = {
    "legacy_reference": "engine_2027_reference.py, inspected as text; never imported or executed",
    "latest_adjustments": "run046.py: form-weighted lineup/quality/finishing; active-player cards",
    "retained": "quality weights, home advantage, Poisson shot counts, beta chance sizes, assist probability, yellow rate, rare injury, bounded ratings/fitness loss",
    "explicit_new_extensions": "bounded goalkeeper/composure/attack finishing, straight/second-yellow reds, exact stints/event sequence, symmetric live tactics, timed injuries, named RNG streams",
    "no_vasco_bonus": "The same quality/tactic/finishing functions apply to every club; identity affects coach profile only",
    "training": "R25 -0.06 opponent xG was consumed historically and is not applied to future/synthetic matches",
    "fitness": "Pregame fitness is the observed checkpoint value; no unplayed intervening matches or recovery is silently assumed",
}
