# Phase 2A engine: execution, configuration and narration

`braga_era.engine` is executable headless Python with no runtime third-party dependencies. The pure match engine accepts immutable snapshots/plans and returns a complete result. It has no database connection, filesystem, UI or host-clock dependency. Version `braga-headless-1.0.0` is a forward model derived from legacy parameters, not a reproduction of historical RNG outputs or an authorization for official play.

```python
from braga_era.engine import EngineConfig, commit_seeds, prepare, simulate_match, validate_match
from braga_era.engine.world import World

snapshot = World(accepted_database).load_pregame("league:333")
config = EngineConfig()
seeds = commit_seeds(snapshot, config, "committed-before-execution")
plans = prepare(snapshot, config, seeds)
result = simulate_match(snapshot, plans, config, seeds)
validation = validate_match(snapshot, result, config)
assert validation.ok, validation.errors
```

The sandbox wrapper records the seed commitment to disk **before** calling `prepare` or `simulate_match`. Output is staged under an exclusive writer lock and published only after validation and source/scratch hash equality. The pure API makes the caller responsible for storing its commitment. A local commitment/manifest detects accidental changes; it is not a signature, external timestamp or adversarial tamper-proof seal.

## Modules and data

| Module | Responsibility |
|---|---|
| `models.py` | Frozen player/team/coach/rules/snapshot/plan/seed/event/shot/performance/result dataclasses |
| `config.py` | Frozen versioned numeric configuration, validation and provenance |
| `world.py` | Read-only database loading, stable IDs, actual recorded squads and fixture eligibility |
| `randomness.py` | SHA256 seed commitment and isolated named `random.Random` streams |
| `coaches.py` | Role, OVR, form, fitness, morale, continuity and bounded imperfect autonomous decisions |
| `match.py` | Regulation chances, finishing, active participants, tactics, substitutions, cards, injuries and proposed postmatch state |
| `validation.py` | Independent chronological replay, eligibility/score/shot/stint/player accounting |
| `narration.py`, `sandbox.py` | Preview, sequential event delivery, sealed final summary and disposable reports |
| `competitions.py` | Future adapter/progression/player-state protocols and pure global agenda ordering |

Snapshots preserve both the actual scheduled kickoff and the earlier observed checkpoint date. A match tested at a future kickoff uses observed fitness/form, with **no** invented intervening games, automatic recovery or historical suspensions. Player table positions are only GK/DF/MF/FW; role fit uses recorded attributes within those buckets. Foreign rosters and a canonical suspension register are absent. Archive #196 is always blocked; active #354 retains its separate identity. Supplied eligibility exclusions also support future registration/suspension adapters. Both teams need 11 eligible players including a goalkeeper.

## Numeric starting model

The authenticated legacy files were read as text, never imported or executed. `engine_2027_reference.py` supplies the baseline; `run046.py` supplies the latest individual-form adjustments. Full serialized configuration and provenance appear in each report.

| Mechanic | Starting values / provenance |
|---|---|
| Quality | .71 club strength + .29 XI OVR + .42 team form + .45 XI form deviation from 6.55 + .02 fitness deviation from 87; legacy/R25 |
| Home/away xG | 1.55 / 1.20; .054 quality-difference slope; bounded targets; legacy |
| Chances | Clipped Poisson, 5–21 shots, lambda 11 + .08 strength deviation from 72; beta(1.5,12) chance sizes scaled to target; legacy |
| Selection | OVR + .05 fitness + .01 morale + 2.1 form deviation + bounded continuity and decision error; latest legacy form weight, no required names |
| Finishing | Form coefficient .25; probability .006–.82; legacy form/bounds with new bounded composure .003, attack .002 and keeper .006 weights |
| Tactics | Symmetric own/opponent xG adjustments for risk; new symmetric live score-aware risk changes; no identity-based match bonus |
| Assists/cards/injury | .72 assist probability, yellow Poisson 1.55 (max four/team), .015 injury/match retained starting values; new .035 straight-red probability/team and coherent second-yellow dismissal |
| Substitutions | Max five players across three stoppages; three planned second-half windows around 59/73/82; positional refresh and injury/GK replacement; new uniform autonomous policy |
| Fitness/ratings | Legacy 3–8 fatigue range scaled to actual seconds, injury penalty, bounded 5.2–9.8 ratings; exact played stints replace legacy rounded 90-minute counters |
| Rolling form | Last four actual league performances, .68 recency decay, square-root minutes weighting and sample shrinkage toward 6.55; no cup history invented |

Formation starts with Braga's asymmetric 4-2-3-1 and 4-4-2 defensive shape. Other coaches have disclosed modeled traits rather than invented named managers. Lineups use positional suitability and bounded imperfect judgement; live coaches consider score, workload, cautioned players and available replacements. A cautious choice can be poor and a favored team can lose. The prior R25 -0.06 training effect is consumed and absent from this model.

Ratings/morale/fitness/form in results are **proposed**, never persisted. Exact rating coefficients, chance bounds and risk effects are versioned in source alongside the frozen configuration. This first model is a starting calibration, not an empirically fitted representation of football. Prematch H/D/A is an independent Poisson approximation from pregame expected xG; live dismissals/tactics/finishing create a different realized distribution.

## Reproducibility and seed policy

1. Canonical JSON serialization is the existing sorted-key UTF-8 `history.digest` convention. Snapshot identity includes source DB SHA256, fixture/kickoff, squads, traits, rules and observed state. Configuration identity includes every dataclass value and the semantic engine version.
2. The root SHA256 hashes `{snapshot, config, seed: str(requested_seed), scope: noncanonical-sandbox}`. Every purpose uses SHA256(root + `:` + purpose), interpreted as a big-endian integer for an isolated Python MT19937 `Random`.
3. Stream names are `coach:CLUB_KEY`, `chance-generation`, `attribution`, `finishing`, `discipline`, `injuries`, `live-coaches`, and `postmatch`. No module uses the global RNG. Stable sorted IDs and explicit sequence numbers remove dependence on set/hash iteration.
4. Do not change the requested seed after seeing a result. Implementation debugging may change a not-yet-released model; diagnostic outputs must retain their own configuration/input hashes. The two final fixed-seed artifacts are noncanonical regression evidence, never desired official scores.
5. Scores are integers; xG is four decimals; chance probability eight; prematch probabilities twelve; ratings one; fitness two; form three. Reports record Python/platform separately. CI compares result digests on Windows/Linux Python 3.11–3.13. Other runtimes need verification; Python distribution implementations may change in future versions.
6. Any future change affecting outcomes needs a forward engine/configuration version and reviewed provenance. Never change approved history, accepted expected hashes, or demo evidence solely to silence a test. Official execution will need a distinct execution namespace/immutable commitment and one-time receipt in Task 03B.

## Event and narration contract

Every event has contiguous `sequence`, elapsed seconds, period, kind, actor/club IDs, pre/post score, and the on-field state after that event. Same-second priority is boundaries, coach changes/substitutions, injury, discipline, then chance; serial scheduling resolves any remaining tie. A shot's GOAL or SAVE follows that shot. This makes an incoming player's same-minute contribution auditable without the old Rojas ordering error.

Regulation is 45 + 45 minutes plus three second-half stoppage minutes. Half-time and second-half kickoff occur at elapsed 2700, with distinct sequence numbers. Final whistle occurs at 5580. Exact stints include stoppage seconds. This first engine does not model first-half added time or additional medical/concussion substitution exceptions.

Generated sandbox files:

| File | Delivery use |
|---|---|
| `seed_commitment.json` | Pregame input/configuration/root seed identity, written before draws |
| `preview.json` | Context, source date, eligible lineups/bench, exclusions and prematch forecasts; no result |
| `private_match_report.json` | Full snapshot/config/result, event sequence, shot/player data, sealed summary and validation; diagnostic spoilers |
| `private_events.jsonl` | Complete authoritative event stream; diagnostic spoilers |
| `validation.json` | Independent replay check count/findings |
| `narration_cursor.json` | Result digest and consumed sequence, updated atomically |
| `scratch.sqlite` | Unchanged disposable source copy, never a new save |

`python -m braga_era narrate DIRECTORY --count 1` delivers the next event and current score only. It removes the shot's later goal/on-target/finishing outcome fields so the following GOAL/SAVE is revealed in sequence. Counts 1–20 are supported. There is no normal seek/replay-to-final command. The final whistle unlocks the postmatch summary and player statistics. If the private result digest changes, narration refuses to continue. Files are local and not encrypted; directly opening the private report or manually changing cursor state bypasses normal spoiler protection.

Hikari narrates only these facts. It must not improvise a scorer, score change, substitution, disciplinary consequence or future result. There is no official runner in Phase 2A.
