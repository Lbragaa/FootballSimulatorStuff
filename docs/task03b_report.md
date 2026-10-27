# Task 03B — chronological world integration and safe development persistence

Implemented a functioning multi-competition world on **NONCANONICAL DEVELOPMENT TEST** copies. The bounded demonstration runs all **16 September 30 continental first legs**, the existing month-end payroll obligation, and **all ten R26 league fixtures**. Results persist once, player state flows across competitions, standings reconcile, and the development package independently restores and deterministically replays. Accepted 046C v2, its approval receipt, original 046, official clock and official R26 status remain unchanged. No official Save 047 exists.

## Baseline and GitHub consolidation

Verified PR #4 head `362327de8fe2e4ebf0ede50a164d81df0e7c8626`, its 46-file Task 03A diff, mergeability and all six green Windows/Linux Python 3.11–3.13 jobs in [CI run 40109062644](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40109062644). The ordinary merge produced **`16c17e414b58a331f3965ec39198fc7b261376ba`** from prior main `6fc4cc0`. An ancestry check and **158 passing tests on the merged baseline** confirmed the new main. No force push, reset or commit deletion was used. See [merge evidence](acceptance/task03b_engine_merge.json).

All Task 03B work is on `codex/task-03b-world-integration`; its PR targets the updated main and is left open for review. Package version is **0.5.0**. Regulation engine **braga-headless-1.0.0** retains both Task 03A regression hashes. The new world, roster/policy and knockout wrapper are separately versioned; details are in [world architecture](world_integration.md).

## Implemented components

| Component | Working behavior |
|---|---|
| Foreign squads | 49 explicitly modeled foreign clubs, 1,276 persistent fictional players, variable 24–28 player depth, stable noncolliding IDs, source/proposal/seed provenance and no real-world roster import |
| Four adapters | Brasileirão, CDB, Libertadores and Sudamericana use stable namespaced fixtures and heterogeneous native field/status mappings, two-leg orientation/aggregates, winners and known CDB next-stage activation |
| Proposed tie rules | No away goals; tied two-leg aggregates go to penalties; single finals use 30m ET then penalties; regulation math/metrics reused and extensions validated |
| Global agenda | Kickoff, match completion and month-end obligations share one timeline; all equal-kickoff inputs come from one pre-state; overlapping 18:00/19:00 matches complete in the correct order |
| Player timeline | Elapsed recovery, current membership/known contracts, archive exclusions, forward competition-specific bans, injury expiry, morale/form, actual dated prior performances and explicit training consumption |
| One-time persistence | Durable pre-draw inputs/config/seeds, separately cached validated results, unique receipts, process locking, atomic simultaneous-group application, rollback and original-seed crash resumption |
| Audit and saves | Exact parent/history/schema checks, reversed full before/after journal, native/overlay accounting, complete deterministic replay, portable DEV-03B package and explicit promotion refusal |
| Hikari | Pregame-only Mirassol preview and persistent match-specific narration cursor; final statistics withheld until final whistle; private diagnostic world report is separate |

Fresh installations now require exact accepted 046C or an explicit historical `--db`. They no longer silently select old 046 as the default. Original historical validation profiles and frozen checksums are unchanged.

## Demonstration and artifacts

```sh
python tools/bootstrap_accepted.py --download --output output/accepted-046c
python -m braga_era world demo --db output/accepted-046c/database.sqlite --output output/my-world-demo --seed task03b-world-demo-v1
python -m braga_era world narrate output/my-world-demo/world --fixture league:332 --count 1
python -m braga_era save verify output/my-world-demo/NONCANONICAL_DEV_03B.zip
python -m braga_era save restore output/my-world-demo/NONCANONICAL_DEV_03B.zip --output output/my-independent-restore
```

The local complete artifact is under ignored `output/task03b-development-v1/`, including the 5,713,141-byte **NONCANONICAL_DEV_03B.zip**, independent restoration, full receipts/results/operations and reports. CI publishes the same kind of portable package and reports as downloadable `NONCANONICAL-world-OS-pyVERSION` artifacts. SQLite save binaries are not committed to Git.

| Verification | Evidence |
|---|---|
| Accepted parent before/after | `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7` |
| Accepted ZIP, unchanged | `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8` |
| Local development archive | `fc5b73ee1cb8237a44ab533f278fcccf573deb79a40ca67198f04881f2da4887` |
| Reproducible football-world digest | `33d9a1899f9b8c724ef97f3eaf4da50bef4a7384426237d0c137bf9b35ccf17d` |
| Persisted receipts | 26 unique: 16 continental + 10 league; zero missing or duplicate applications |
| Resumption | Already applied run makes no match draws and changes no football-state hash |
| Rest | Exact inherited Coritiba league:382 → league:393, 69h, disclosed; no introduced sub-72h interval |
| Month-end | September due R$1,799,666.67 posted once by the existing contract-backed payroll function; budgets/reserve and original ledger rows preserved |
| Development clock | Last completed event 2027-10-03 20:33; the official accepted clock remains 2027-09-26 23:30 |

The archive's physical bytes may vary with SQLite/compression/runtime layout; the accepted parent bytes and logical world/result hashes are the portability gates. [Demonstration proof](validation/task03b_demo.json), [roster distributions](demos03b/roster_distribution.json), [all 16 resolved preflight entries](demos03b/september30_preflight.json), [spoiler-safe summary](demos03b/world_progress.json), and [Mirassol pregame preview](demos03b/mirassol_pregame.json) are inspectable text evidence. [Private full world progress](demos03b/private_world_progress.md) contains match results and the resulting table, including the noncanonical Vasco outcome; it must not be supplied as normal pregame narration context.

The preview was captured after all earlier continental/payroll commitments and before the simultaneous October 3 group. No official Mirassol–Vasco result is implied by this disposable test. A separate test run through October 16 validates continental return legs, 16 qualified clubs, eight new CDB QF legs and activation of both semifinal pairings.

## Tests and safety limits

Regression coverage includes stable modeled identities/distributions; four adapters; valid/invalid dependencies; aggregates, ET and shootouts; simultaneous and overlapping fixtures; cross-competition fitness/form/eligibility; suspensions/registration/contracts/injuries/training; already-final/claimed fixtures; no reroll on repeat; real process termination and concurrent runners; injected failures after claim/result/simulation/during apply/before and after commit; atomic rollback; payroll idempotency; historical/calendar/finance/schema/journal tampering; wrong parent and unsupported versions; malformed/re-sealed exports; fresh restoration and spoiler-safe cursor continuation. Detailed completed local/CI counts are recorded with the final verification evidence.

The final local suite passed **197 tests, zero failures/skips, in 406.61 seconds** on Windows Python 3.12.14. [Local evidence](validation/task03b_local.json) records both unchanged source hashes and the full frozen 046/accepted 046C audits (27/36 checks, zero failures, ten disclosed warnings each). An isolated 0.5.0 wheel, with site packages disabled and execution outside the repository, independently restored/replayed the development archive and resumed narration at kickoff. The CI workflow runs the full suite, both legacy engine digest regressions, full world demo, exact logical-world comparison and checkpoint export/restore on Windows/Linux Python 3.11–3.13. JUnit XML and portable development packages are uploaded per job; the Task 03B PR links the final run and its six job results.

Inspected squad distributions: depths 24/25/26/27/28 occur for 11/7/11/9/11 clubs respectively; club power ranges 69.1–80.0 and squad mean OVR 66.796–77.818. The bounded demo produces ten pending forward suspension rows. No rare injury occurred in that fixed-seed 26-match sample; forced injury/red-card tests verify persistence, recovery eligibility and discipline rather than selecting a different demonstration seed. The portable payload is 51,541,691 bytes uncompressed, within the inherited 100MB safety limit; larger future worlds require an explicit scaling/profile decision rather than silently lifting archive limits.

Known limits requiring decisions before official gameplay:

- Roster generation, recovery, registration priors and discipline thresholds are proposed forward policies. Historical bans and untracked contracts are unknown; generated player identities are not retroactive historical observations.
- Knockout tie-breaks and single-final venue/home advantage were not fully specified in source rules. The declared proposal is exercised in tests, not canonically approved. ET currently retains the final XI and has no additional ET cards/injuries/substitutions.
- CDB follows recorded next_tie; continental later-round draw mappings remain genuinely unresolved conditional reservations. Advancement stops there instead of inventing participants or skipping matches.
- Transactions are atomic per simultaneous group. Earlier completed groups and durable commitments/results survive a later failure so runs can resume safely. New unlogged external mutations fail journal/replay verification; future training/transfer input APIs need reviewed provenance before production use.
- File locks/SQLite transactions are tested across process crashes, not a guarantee against arbitrary disk/cloud-sync/power failures. Local spoiler sealing is a delivery gate, not encryption or access control.

The focused next step is [Task 03C](task03c_plan.md): approve/calibrate the proposed world and competition policies, resolve continental draw rules, run extended integration checks, then design a separate explicit official-play authorization/profile gate. No official execution or promotion is authorized by Task 03B.
