# Task 03 technical design: modular, headless simulation engine

This is a design only. Task 02B implements no match engine, official match execution, R26 result or fictional clock advance. The accepted world remains Save 046 until the commissioner explicitly accepts a candidate. The proposed 046C v2 calendar is a separate administrative change, not a simulation input authorized for official execution yet.

## Evidence and compatibility boundary

Inspect the current SQLite universe, `reference/engine_2027_reference.py` and `reference/run046.py` as text/AST only. Both legacy files perform top-level writes; run046 patches sliced Python source and executes it. Do not import, replay or reuse that execution pattern. The original engine file is a historical Round 1 baseline; run046 shows the actual Round 25 adjustments. Engine labels in `meta` and zero-filled audit rows do not prove complete historical reproducibility.

Preserve these inherited starting mechanics in explicit versioned configuration before introducing calibrated future changes:

- SHA256-derived per-fixture RNG seed: the old helper hashes hyphen-joined arguments, takes 15 hex digits and seeds `random.Random`. Legacy round calls use `braga2027` and fixture ID. A new version may use isolated named streams, but must precommit its algorithm/configuration and never rewrite prior results.
- Team quality blends club strength, XI average OVR, team form, average individual form and fitness. The baseline uses .71/.29 strength/XI weights. R25 changes the team-form coefficient from .22 to .42 and adds .45 times the XI form deviation from 6.55. Fitness contributes .02 times deviation from 87.
- Home/away chance targets start from 1.55 and 1.20 with .054 times quality difference and bounded xG ranges. Baseline shot count is clipped Poisson, 5–21 shots; beta-distributed chance sizes are scaled to the xG target. R25 samples finishing with individual-form adjustment, bounded probability .006–.82. Explicit keeper/tactical extensions must be separately configured, evaluated and versioned; do not claim the supplied baseline already models every desired mechanism.
- R25 lineup scoring adds 2.1 times individual-form deviation to OVR/fitness/morale. Role targets, preferred tactics and continuity currently mix hardcoded names and position buckets. Translate these into an autonomous coach policy using IDs, tactical fit and bounded familiarity; retain Braga's current philosophy without guaranteeing his preferred XI or a victory.
- Score-aware substitutions and active-player tracking are fundamental. Old triggers are 59/73/82 for Vasco and 65/78 for background teams. These become coach-specific configurable decision windows; choices may be suboptimal. No user intervention changes them unless explicitly authorized.
- Existing yellow cards, rare muscle injuries, fitness expenditure, morale, ratings, rolling form, shots and assists remain part of the model. R25's form uses the last four league performances with recency decay .68 and minutes weighting. Explain scope before blending cup performance into a new all-competition model.
- The R25 defensive-training effect was a one-match, precommitted -0.06 opponent xG adjustment. It is consumed historical evidence, not a permanent bonus to carry into R26. Existing home tactical modifiers must become explicit tactic parameters, not protagonist favoritism.

Historical results are not golden outputs to reroll with the new engine. Characterization tests compare extracted pure math/selection rules on disposable synthetic states. Forward model versions retain genuine win/loss/injury uncertainty and must never be tuned after an official outcome is observed.

## Domain boundaries and interfaces

Use standard-library dataclasses/enums and immutable input objects. No Streamlit, browser, hosted server or global SQLite connection belongs in the engine.

| Component | Input / output and responsibility |
|---|---|
| World reader | Accepted checkpoint hash, competition/season and fixture ID → immutable `PregameSnapshot`; read-only SQL, no live mutable rows |
| Eligibility | Snapshot → eligible IDs plus explicit exclusion reasons: injury, suspension, registration/contract evidence, archive resolution; always block archived Savarino #196 while retaining #354 and every old attribution |
| Coach policy | Snapshot, coach characteristics, RNG stream → `MatchPlan` with XI, bench, shape, roles, risk and decision rationale; autonomous for both clubs |
| Engine configuration | Frozen `EngineConfig` with semantic version, math/calibration parameters, event/injury/discipline policies and rounding rules; canonical serialized hash |
| Seed commitment | Parent hash, fixture identity, engine/config hash and approved execution ID → `SeedCommitment`; store before running, isolate lineup/chance/finishing/discipline/injury streams |
| Pure match engine | `simulate_match(snapshot, home_plan, away_plan, config, seeds) -> MatchResult`; no SQL, filesystem, wall-clock reads or outcome search |
| Match validator | Snapshot/result → typed findings; fail before any official save publication |
| Official runner | Explicit authorization, accepted parent and selected scheduled fixtures → validated next candidate; owns lifecycle, locks, atomic transaction and one-time execution receipts |
| Narration exporter | Result → ordered `NarrationEvent` stream and separately sealed post-final-whistle summary; does not create facts |
| Forecast service | Immutable snapshot plus forecast-specific streams → distributions/scenarios in an analytical namespace; no official write access |

`PregameSnapshot` includes stable player/club IDs, observed source-table values, scheduled kickoff, competition and season labels, coach profile, available fitness/form, last actual match/recovery timestamps, ruleset, calendar context and training effects with consumption identity. Missing data remains marked unknown or uses a documented explicit model prior; never fabricate historical observations.

`MatchResult` contains fixture identity, engine/config/input/seed hashes, complete events, shots/chance probabilities, lineup and stint data, injuries/cards/substitutions, ratings and proposed postmatch deltas. No method can mutate the source snapshot or choose a different seed after seeing a score.

## Event ordering and narration

Use a monotonic sequence number as the authoritative tie breaker. Record period, elapsed seconds, display minute/stoppage notation, event type, actor/club IDs, causal parent IDs, score before/after and structured payload. Apply a substitution to on-field state before an incoming player's same-minute action. Never sort tied events by player name/type or rely on minute alone; that caused the inherited Rojas JSON discrepancy.

Model stoppage time separately from rounded participation totals. The inherited engine can generate shots at minutes 91–93 while appearance counters use 90; future eligibility validation must use actual entry/exit intervals and event sequence rather than assume every event minute must be <= recorded rounded minutes.

Narration interfaces should expose preview, kickoff, chronological events, interval and final whistle before making the final score/round table accessible. Keep the complete result stored privately for integrity, but the ChatGPT delivery cursor must not include postmatch headlines, other final results or future score changes prematurely. Reopening an episode resumes the stored sequence, not simulation.

## One-time official execution and transactional persistence

1. Require an explicit new user instruction for official execution. Verify the accepted registry parent and candidate acceptance decisions; Task 02B does not supply either authorization.
2. Build a global chronological due-event agenda. The proposed v2 first continental legs are September 30, before R26 starts; do not jump directly to October 3 while leaving those competitions overdue. Clarify official checkpoint/episode numbering for multiple competitions rather than assuming Save047 always means one league round.
3. Reject a final or already-claimed fixture before allocating RNG. Check the complete round inventory: ten scheduled league matches, 20 distinct participating clubs, correct season, dates and parent history. Due cup events need their own adapters and rules.
4. Persist an execution commitment on a disposable workspace before running. A crash retries the same committed inputs/seed or resumes stored results; it must not generate a fresh official result. Distinguish claim, simulated, validated, committed and exported states.
5. Simulate purely, validate every result, then apply all authorized outcomes inside one scratch SQLite transaction. Use a unique execution/fixture receipt to prevent double application. Round batching may include matches on different dates, so recovery and coach state must follow the chronological agenda, not one blanket recovery operation.
6. Recompute all affected standings/totals from recorded outcomes; validate both unchanged parent history and exact permitted forward deltas. No parent overwrite. Publish a new checkpoint only after audits, complete operation logs and restoration verification.
7. Export one portable package with database, provenance, precommitted inputs/config/seeds, chronological event JSON, episode cursor/report and validation evidence. Keep prior accepted artifacts immutable and use external archive storage, not endlessly nested binaries in Git.

Recovery must be elapsed-time based across league/cup commitments. Do not apply the legacy +6 fitness weekly-round recovery twice when a club has multiple competitions. Persist injury onset, recovery eligibility, workload and training consumption IDs. Model future tactical familiarity and chemistry slowly with bounded effects; a winning result never justifies a retrospective OVR increase.

Financial changes are separate administrative obligations. Do not charge annual wage commitments again, invent attendance revenue without an explicit receipt model, or release new owner capital because a calendar year changes. September month-end posting must reuse the validated idempotent payroll logic and its player-level evidence.

## Validation and new schema proposal

Propose versioned additive tables for engine versions/configuration, immutable input snapshots, seed/execution commitments, fixture receipts and exact event sequence. Preserve the existing player/fixture IDs and all frozen 046 sporting history. A migration specification must explain mappings between domestic `fixtures`, separate CDB leg keys and continental table-specific identities; integer fixture IDs are not a global competition namespace.

Match validation must prove: eligible unique XI (11 each), legal bench and stints, active actors for shots/goals/cards, correct substitution/dismissal order, coherent score trajectory, scored shots = goal events = fixture goals = player goals, assists attributed to on-field teammates, on-target accounting and documented xG precision tolerances. No invented missing legacy metrics. Validate possession bounds, fitness/morale changes, injuries, disciplinary state and deterministic hashes.

Round/world validation must prove: correct inventory and chronology; no duplicated official execution; derived league W/D/L/points/GF/GA; immutable completed parent records and identities; unchanged unauthorized finances/competitions; budget/reserve constraints; calendar rest/workload; provenance and restorable exports. Forecast data can never satisfy an official fixture receipt or advance a canonical counter.

## Implementation milestones for Task 03

1. **Contracts and characterization:** immutable typed snapshots/config/results, read-only adapters, explicit rule/math extraction from legacy source, synthetic math/eligibility tests. No official CLI yet.
2. **Pure single-match core:** deterministic chance generation, player/keeper quality, form/fitness/tactics, active stints, substitutions, cards/injuries and exact event sequence. Validate same-seed identity and diverse outcomes on synthetic scenarios, without rerunning settled matches.
3. **Autonomous coach behavior:** role/eligibility constraints, current Braga philosophy, continuity, risk, fatigue and score-aware decisions for all clubs. Store explanations and preserve the possibility of poor decisions/results.
4. **Persistence and crash safety:** explicit commitment/receipt migrations, scratch transactional apply, duplicated-fixture rejection, rollback/crash recovery, immutable-parent checks and round/cup adapters. Define seed/profile/version compatibility.
5. **Narration/export and analytical separation:** spoiler-safe event cursor, final-whistle gate, portable packages and independently isolated Monte Carlo forecasts. Add headless CLI tests and Linux/Windows CI.
6. **Commissioner review before first official execution:** approve the administrative calendar/candidate, future engine version/calibration and seed policy, the chronological due-event plan and an explicit execution request. Only then consider the next official checkpoint. Never treat passing tests as permission to simulate.

These milestones are the proposed next task, not work performed in Task 02B. If the commissioner chooses the alternative 2028 postseason instead of recommended B, settle season-label/date separation, expired contracts/registration eligibility, preseason congestion, 2028 competition entries and financial authority first; do not silently roll the universe or renew players.
