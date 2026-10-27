# Task 03A — administrative acceptance and first playable engine

The exact approved **046C v2** was accepted administratively. A functioning modular headless engine now produces complete, independently validated noncanonical match reports. Original 046, rejected v1, all settled history and fictional time are preserved. No official fixture has been executed and no Save 047 exists.

## Acceptance and durable artifact

| Artifact | Verified SHA256 |
|---|---|
| Original handoff ZIP | `527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719` |
| Original Save 046 DB | `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28` |
| Accepted 046C v2 DB | `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7` |
| Accepted 046C v2 ZIP | `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8` |

Both approved hashes matched the reviewed artifacts. The full 046C profile passed **36 checks, zero failures, 10 disclosed warnings**, and an independent restoration passed before the existing explicit `promote_candidate` API wrote the real local registry. The [approval receipt](acceptance/046C_v2_approval.json) records commissioner authority, instruction hash, implementation, hashes, policy approvals and unchanged date. Immutable package metadata remains `candidate`; acceptance is external so no approved byte changes.

The [published release](https://github.com/Lbragaa/FootballSimulatorStuff/releases/tag/save-046c-v2) provides the [exact accepted ZIP](https://github.com/Lbragaa/FootballSimulatorStuff/releases/download/save-046c-v2/Save046C_v2_accepted.zip), approval receipt and SHA256 inventory. The released receipt SHA256 is `f000e0df48fd42c4f955f19add2db62762372ca2be12e3b5ef915dada24d015f`. Fresh installations use `tools/bootstrap_accepted.py`, which verifies exact ZIP/DB hashes and independently restores without promotion.

Accepted decisions: strategy B's 70 future kickoff changes (36 dates, 34 times), 72h kickoff-to-kickoff including travel, the inherited 69h Coritiba exception, contract-based payroll accounting and board-objective reconciliation. Foreign schedules/travel routes remain unknown. Cash R$30.55m, September unpaid accrual R$1,559,000.01, R$16m reserve and all acquisition authority remain as reviewed. Historical candidate-era warning wording remains inside the immutable package/profile; the external acceptance receipt supplies the subsequent decision.

## GitHub consolidation

All three latest PR heads had passing six-job Windows/Linux CI and were merged in dependency order with merge commits. PRs #2 and #3 were retargeted to updated `main` and their remaining diffs inspected. No force-push or commits were discarded.

| PR | Reviewed head | Merge commit | Passing CI run |
|---|---|---|---|
| [#1](https://github.com/Lbragaa/FootballSimulatorStuff/pull/1) | `732c3ef` | `7acf293743b3542bd63984d090b966ece1c68564` | [40100351558](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40100351558) |
| [#2](https://github.com/Lbragaa/FootballSimulatorStuff/pull/2) | `abbf7f8` | `c747d0cf8c9f3495d81f8ebd6d0f99a1d6587a90` | [40100367611](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40100367611) |
| [#3](https://github.com/Lbragaa/FootballSimulatorStuff/pull/3) | `509555d` | `6fc4cc0d7b455af1538b4f3ada43a30c6700bd29` | [40103665362](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40103665362) |

Task 03A uses the single branch `codex/task-03a-engine` from consolidated main `6fc4cc0`, published as [PR #4](https://github.com/Lbragaa/FootballSimulatorStuff/pull/4), left open for review. The engine implementation is commit `baaa85c91c9555375d20c808038ba8b3004d606c`. [Detailed merge evidence](acceptance/engineering_merges.json) also records two initial automatic-approval rejections resolved by re-presenting exact user authorization and public fictional-data evidence; the same intended actions then succeeded. No permission blocker remains.

## Implemented engine and integration

The [engine guide](engine.md) documents contracts, legacy numeric parameters, explicit new effects, version `braga-headless-1.0.0`, SHA256/named-stream seed policy, rounding and Hikari delivery. Code separates immutable snapshots, eligibility, autonomous coaches, pure regulation simulation, independent chronological auditor, read-only world adapters, disposable sandbox and narration. Package version is 0.4.0.

Both teams autonomously select eligible database IDs using positional fit, OVR, current form/fitness/morale, continuity and imperfect judgement. Braga retains his current 4-2-3-1/4-4-2 identity without guaranteed names or a victory. The engine records chances, xG, finishing/keeper effects, goals/assists, saves, yellows/reds, injuries, tactical changes, substitutions, exact stints, ratings and proposed fitness/morale/form. The one-match R25 training effect is not repeated. Stable sequence and exact on-field state resolve same-minute ordering.

No official SQLite writer exists in this implementation. The engine rejects official scope, settled fixtures and requested extra-time/shootout execution. Competition/global-agenda/player-state protocols prepare Task 03B without pretending to resolve cups or advance calendars. Normal Hikari delivery starts with preview and advances a persistent cursor; postmatch is released only with the final whistle. Private full reports deliberately contain diagnostic spoilers.

## Complete disposable demonstrations

All **16 September 30 continental fixtures** lack at least one foreign recorded player squad. The loader fails with `MissingRoster` instead of inventing players. [Preflight evidence](demos/september30_preflight.json) lists every blocker. The requested preference therefore uses an existing scheduled domestic fixture as fallback, alongside the separate synthetic Vasco test.

| NONCANONICAL demonstration | Seed | Score | Shots | xG | Independent checks |
|---|---|---|---|---|---:|
| Real scheduled league:333, Palmeiras–Goiás | `task03a-engine-smoke` | 4–1 | 16–11 | 2.0180–0.5695 | 751 |
| Synthetic current-squad Vasco–Fluminense | `task03a-vasco-synthetic` | 2–0 | 10–12 | 1.4797–1.2787 | 642 |

These are **NONCANONICAL TEST SIMULATION** results, never official fixture scores or a Mirassol R26 result. Source and disposable copies retained the exact accepted DB SHA256 before/after. No outcome-based seed selection was used. Implementation smoke outputs during development had their own input/config hashes; the final reports commit the released starting configuration and original requested demonstration seeds.

[Complete readable lineups, events and player ratings](demos/README.md), [league JSON](demos/league333.json), [synthetic Vasco JSON](demos/vasco_synthetic.json), and companion ordered JSONL/preview exports are committed as text evidence. Runtime output under ignored `output/` also contains scratch copies, seed files, cursors and validation. No accumulating save binaries enter Git.

## Validation and remaining boundary

Local comprehensive suite: **158 passing tests** (history/checkpoints plus 63 engine/acceptance tests), 99.10 seconds. Coverage includes reproducibility, varied seeds/Vasco losses, independent replay of forced injuries/dismissals, unique eligible XI, stable same-clock substitution/shot order, active scorers/assisters/keepers, xG/player accounting, changed-report/summary rejection, source immutability, accepted registry/path precedence, external-directory CLI use and spoiler-safe cursor continuation. Local sandbox TEMP/TMP were explicitly placed in ignored workspace scratch to accommodate the desktop sandbox's temporary-directory permissions. A built 0.4.0 wheel was installed into an isolated target and exercised outside the repository with site packages disabled; accepted catalog, sandbox and narration worked. A fresh public release download independently restored the exact approved DB.

All six Windows/Linux Python 3.11, 3.12 and 3.13 jobs passed on engine implementation `baaa85c`: [CI run 40108799493](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40108799493), [machine-readable job/log evidence](validation/task03a_ci.json). Each log confirms **158 tests passed** and both exact demo result hashes matched across all platforms/versions. CI downloaded/authenticated the accepted release, ran full audits/checkpoint export/restore, exported both sandbox reports and uploaded JSON/JSONL artifacts. Later documentation-only commits preserve this tested engine implementation; PR #4 checks show the current branch status.

Remaining limits: missing foreign player data; no reliable historical suspension register; observed fitness without future recovery; regulation only; coarse source positions and modeled opposing coach traits; no official persistence, multi-competition player timeline or bracket progression. The next task is [Task 03B](task03b_plan.md): resolve approved roster/rule evidence, implement chronological adapters and one-time transactional persistence, and validate restorable future candidates before any explicit official execution request.

Canonical fictional state remains **2027-09-26 23:30**. Vasco–Palmeiras R25 remains final **3–2**. Mirassol–Vasco on **October 3, 16:00** remains scheduled; continentals on September 30 must precede it in a future official runtime.
