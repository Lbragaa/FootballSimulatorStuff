# First official batch — unsigned review template

**NOT AUTHORIZATION. No production key, registry or official match is created by this document.**

Root and immediate parent: accepted Save 046C v2, DB SHA256 `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`; official clock 2027-09-26 23:30.

Proposed boundary: **2027-09-30 23:59**. All 16 first legs below kick off on September 30 at 16:00. The group uses one common pre-kickoff state; persistence follows deterministic fixture ordering. No league fixture or Vasco outcome is included.

| Fixture identity | Home | Away |
|---|---|---|
| `lib:LIB-R16-01:L1` | Bolívar | Palmeiras |
| `lib:LIB-R16-02:L1` | Junior de Barranquilla | Fluminense |
| `lib:LIB-R16-03:L1` | O'Higgins | Vélez Sarsfield |
| `lib:LIB-R16-04:L1` | Atlético-MG | River Plate |
| `lib:LIB-R16-05:L1` | Estudiantes | Santos |
| `lib:LIB-R16-06:L1` | Huachipato | Flamengo |
| `lib:LIB-R16-07:L1` | The Strongest | Liverpool (URU) |
| `lib:LIB-R16-08:L1` | Atlético Nacional | Sportivo Luqueño |
| `sula:SULA-PO-01:L1` | Caracas FC | San Lorenzo |
| `sula:SULA-PO-02:L1` | Platense | Emelec |
| `sula:SULA-PO-03:L1` | Sporting Cristal | São Paulo |
| `sula:SULA-PO-04:L1` | Athletico-PR | Peñarol |
| `sula:SULA-PO-05:L1` | Rosario Central | Libertad |
| `sula:SULA-PO-06:L1` | Universitario | Universidad Católica |
| `sula:SULA-PO-07:L1` | Bragantino | Independiente |
| `sula:SULA-PO-08:L1` | Newell's Old Boys | Botafogo |

One administrative obligation follows: `payroll:2027-09` at 23:59, using the existing contract-backed actual-day payroll policy. It must be posted exactly once. Do not add base payroll, capital, revenue, awards, transfers or budget authority. September 26 accrued liability remains an immutable parent observation; full month-end due is recomputed from the approved contract policy.

Proposed versions: continuous-forward-lineage-2; seed policy career-stable-per-fixture-1; foreign squads fictional-squads-1.0.0; engine configuration braga-headless-1.1.0; world policy world-proposals-2.1.0; knockout extension braga-knockout-2.1.0. The policy bundle remains pending commissioner acceptance.

After a distinct future instruction permits production trust bootstrap, the trusted worker must prepare the actual manifest from the authenticated parent. Human-supplied fields are commissioner identity, career ID, first execution ID and the one career seed committed before outcomes. Preparation fills its commitment hash, exact configurations and inventory. There is no new seed parameter in later batches.

Template shape (placeholders make this non-executable):

```json
{
  "profile": "continuous-forward-lineage-2",
  "career": "<COMMISSIONER_CHOSEN_CAREER_ID>",
  "test_only": false,
  "commissioner": "<HUMAN_COMMISSIONER>",
  "execution_id": "<FIRST_EXPLICITLY_AUTHORIZED_BATCH_ID>",
  "immediate_parent_sha256": "27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7",
  "immediate_parent_database_sha256": "27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7",
  "generation": 1,
  "until": "2027-09-30 23:59",
  "fixtures": [
    "lib:LIB-R16-01:L1",
    "lib:LIB-R16-02:L1",
    "lib:LIB-R16-03:L1",
    "lib:LIB-R16-04:L1",
    "lib:LIB-R16-05:L1",
    "lib:LIB-R16-06:L1",
    "lib:LIB-R16-07:L1",
    "lib:LIB-R16-08:L1",
    "sula:SULA-PO-01:L1",
    "sula:SULA-PO-02:L1",
    "sula:SULA-PO-03:L1",
    "sula:SULA-PO-04:L1",
    "sula:SULA-PO-05:L1",
    "sula:SULA-PO-06:L1",
    "sula:SULA-PO-07:L1",
    "sula:SULA-PO-08:L1"
  ],
  "obligations": [
    "payroll:2027-09"
  ],
  "seed_policy": "career-stable-per-fixture-1",
  "career_seed_sha256": "<COMMITMENT_FROM_TRUSTED_BOOTSTRAP>",
  "policy": {
    "version": "world-proposals-2.1.0",
    "roster_version": "fictional-squads-1.0.0",
    "roster_seed": "task03b-fictional-rosters-v1",
    "recovery_per_day": 1.5,
    "yellow_threshold": 3,
    "red_suspension_matches": 1,
    "unknown_historical_bans": "unknown; forward counters start at zero, never a historical assertion",
    "registration_prior": "current recorded club membership except archived identities; honor known signing contract dates",
    "cup_tie_policy": "proposal: no away goals; two-leg ties direct penalties; single finals 30m extra time then penalties",
    "draw_policy": "committed seeded stage draws v1; SULA group winners host return R16; later rounds open draw",
    "canonical_approval": false,
    "extension_version": "braga-knockout-2.1.0",
    "journal_policy": "content-addressed-row-images-1"
  },
  "configurations": {
    "normal": {
      "version": "braga-headless-1.1.0",
      "club_quality_weight": 0.71,
      "xi_quality_weight": 0.29,
      "team_form_weight": 0.42,
      "individual_form_weight": 0.45,
      "fitness_quality_weight": 0.02,
      "home_base_xg": 1.55,
      "away_base_xg": 1.2,
      "quality_difference_xg": 0.054,
      "shot_count_lambda": 11,
      "shot_strength_coefficient": 0.08,
      "shot_minimum": 5,
      "shot_maximum": 21,
      "chance_beta_a": 1.5,
      "chance_beta_b": 12,
      "finishing_form_weight": 0.25,
      "lineup_form_weight": 2.1,
      "goalkeeper_probability_weight": 0.006,
      "composure_probability_weight": 0.003,
      "finishing_attack_weight": 0.002,
      "assist_probability": 0.72,
      "yellow_lambda": 1.55,
      "maximum_yellow_events_per_team": 4,
      "straight_red_probability_per_team": 0.035,
      "injury_probability_per_match": 0.015,
      "injury_absence_days": 5,
      "fitness_loss_min": 3,
      "fitness_loss_max": 8,
      "maximum_substitutions": 5,
      "maximum_substitution_windows": 3,
      "stoppage_minutes": 3,
      "live_attack_xg_multiplier": 1.08,
      "live_caution_xg_multiplier": 0.94,
      "missing_player_xg_penalty": 0.1,
      "isolated_rng_streams": true,
      "lineup_fitness_weight": 0.12,
      "neutral_final": false
    },
    "neutral_final": {
      "version": "braga-headless-1.1.0",
      "club_quality_weight": 0.71,
      "xi_quality_weight": 0.29,
      "team_form_weight": 0.42,
      "individual_form_weight": 0.45,
      "fitness_quality_weight": 0.02,
      "home_base_xg": 1.375,
      "away_base_xg": 1.375,
      "quality_difference_xg": 0.054,
      "shot_count_lambda": 11,
      "shot_strength_coefficient": 0.08,
      "shot_minimum": 5,
      "shot_maximum": 21,
      "chance_beta_a": 1.5,
      "chance_beta_b": 12,
      "finishing_form_weight": 0.25,
      "lineup_form_weight": 2.1,
      "goalkeeper_probability_weight": 0.006,
      "composure_probability_weight": 0.003,
      "finishing_attack_weight": 0.002,
      "assist_probability": 0.72,
      "yellow_lambda": 1.55,
      "maximum_yellow_events_per_team": 4,
      "straight_red_probability_per_team": 0.035,
      "injury_probability_per_match": 0.015,
      "injury_absence_days": 5,
      "fitness_loss_min": 3,
      "fitness_loss_max": 8,
      "maximum_substitutions": 5,
      "maximum_substitution_windows": 3,
      "stoppage_minutes": 3,
      "live_attack_xg_multiplier": 1.08,
      "live_caution_xg_multiplier": 0.94,
      "missing_player_xg_penalty": 0.1,
      "isolated_rng_streams": true,
      "lineup_fitness_weight": 0.12,
      "neutral_final": true
    }
  },
  "required_approvals": [
    "rosters",
    "historical_unknowns",
    "engine_configuration",
    "player_timeline",
    "competition_rules_and_draws",
    "financial_restrictions",
    "specified_batch"
  ]
}
```

Execution decision template: `action=authorize_lineage_batch`, profile/career/mode/commissioner, exact actual manifest SHA256 and the complete reviewed approval inventory. The commissioner must review and supply this decision separately. A prepared template or an assistant-generated signature is not consent.

Successor acceptance template: `action=accept_lineage_checkpoint`, same profile/career/mode/commissioner, exact independently verified candidate hash, immediate parent hash and package hash. This is a different decision after execution/restoration. Neither decision has been given for production.

Next boundary after the first successor is accepted: October 3 at 23:59, all ten R26 games including Mirassol–Vasco at 16:00. It requires its own manifest and execution/acceptance decisions from the newly accepted parent. Do not treat this planning note as authorization.
