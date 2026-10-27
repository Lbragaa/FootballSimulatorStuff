# Task 03C — implementation and commissioner review

All simulation evidence is **NONCANONICAL DEVELOPMENT TEST**. The accepted world
remains exact Save 046C v2, **2027-09-26 23:30**. No official match, Save 047,
production execution approval, canonical registry update or release modification
has been performed. Vasco 3–2 Palmeiras remains final; Mirassol–Vasco on October 3
at 16:00 remains officially unplayed.

## Consolidation and preservation

PR #5 was inspected at exact head
`69cc6e189ef027b1f25117dd5dfdb33f38fc3839`. Its ancestry and protected-file diff
matched Task 03B, it was cleanly mergeable, and all six Windows/Linux Python
3.11–3.13 jobs passed (Actions run `40448172419`, 197 tests/job, engine and world
regressions). It was merged with ordinary merge commit
`7a145b98ffc6096d42423d0ea9219dac1cad8e75`; ancestry was retained. All six jobs
also passed on resulting main (run `40577456389`). Work continued on the single
branch `codex/task-03c-final-readiness`; the Task 03C PR remains open for review.

Local unchanged-baseline verification: **197 passed in 381.33 seconds** on
Windows/Python 3.12.14. The previous regulation engine and its two result hashes,
Task 03B world hash, original baseline, accepted approval receipt and accepted
release bytes are preserved. No original historical result or player identity is
repaired implicitly.

Accepted DB: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`.
Accepted ZIP: `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`.

## Implemented forward layers

Package version is 0.6.0. Existing `braga-headless-1.0.0` regulation and
`braga-world-1.0.0` core protocol remain available. The separately registered
forward configuration is `braga-headless-1.1.0`; proposed world policy is
`world-proposals-2.1.0`; ET extension is `braga-knockout-2.1.0`. Preliminary
Task 03C 2.0 evidence has a compatibility registration and is not silently
reinterpreted as 2.1. No previously committed preliminary match is rerolled in
place to apply a corrected model.

`world create --policy readiness-v2` selects the new proposal explicitly; default
creation and the Task 03B demo continue selecting V1. Foreign roster generation
uses its independent unchanged V1 inputs, so changing world mechanics does not
regenerate a different foreign squad. Every modeled ID, attribute and provenance
record is preserved across the two policy initializations.

`world/progression.py` implements complete continental draws/progression and
champion reconciliation. It waits for actual preceding-stage winners, stores a
draw commitment transactionally before drawing, and resumes the same commitment
after a crash. No country/group restriction is invented. SULA R16 uses its eight
recorded group winners against actual playoff winners, with group winners hosting
the return. Later SULA/LIB stages use committed open draws. Each concrete fixture
expands an existing approved reservation at its kickoff; dependencies on a round
reservation resolve only after all its concrete legs finish. Reservations remain
as immutable conditional slots, not fake completed matches. They leave the agenda
only when a validated concrete draw owns them. CDB retains its recorded
`next_tie` bracket and disclosed administrative home ordering.

Single finals use neutral xG and proposed ET/pens. ET has two 15-minute periods,
an interval, up to six total replacements, one additional live stoppage window,
interval substitutions, cautions, second cautions, dismissals, injuries, goalkeeper
replacement or an identified emergency keeper. Shootout takers are the eligible
final players reduced to equal numbers while retaining the defending keeper.
Shootout goals never enter match goals, xG or player goal totals; shootout seconds
do not enter playing minutes/fatigue. No winner is manufactured below seven
players or after an unresolved capped shootout. Independent event chronology,
identity, score, shot-goal and stint accounting supplements exact extension replay.

Forward lineups give fitness a larger selection weight (.12 versus .05). All
clubs still use autonomous coaches with bounded imperfect judgement; there is no
Vasco success or starter guarantee. A shared player overlay supplies chronological
form, morale, registration/contracts, bans, recovery timestamps and training
consumption IDs across competitions. No new invented historical ban/injury is
added. Archived #196 and active #354 remain distinct.

## Season evidence and defects found

The bounded Task 03B demonstration is preserved. Task 03C runs the complete
remaining 2027 agenda: **217 fixtures** = 130 league + 13 CDB + 29 LIB + 45 SULA.
That includes both continental finals, all CDB QF/SF/final legs, the remaining
league schedule, four month-end obligations and four reconciled champions. The
source's 250 settled league games plus 130 prospective games produce 380, with
every club on 38 played. There is no future continental qualification allocation
or invented financial award.

The first long run found a previously unexercised payroll insert placeholder
mismatch when a new month required its seven-column obligation rows. The fix uses
the existing contract/payroll implementation and preserves September's existing
idempotent registration. A later simultaneous LIB final/SULA semifinal exposed a
configuration persistence bug: every fixture now stores its own committed config,
including the neutral-final variant, rather than a group's last config. A dedicated
mixed-configuration test verifies each stored config against its seed commitment.
Failed disposable runs remain diagnostic; accepted data and released engine
regressions were unaffected.

Two initial 2.0 season scenarios completed and were audited. A later shootout
eligibility review produced version 2.1 to retain the defending goalkeeper during
reduce-to-equate. Final scenarios use fresh explicitly versioned development
identities and fixed seeds selected before outcomes, with the prior model/evidence
kept available. Seeds are never selected for favorable football results.

Final primary command:

```text
python tools/stress_season.py --db output/Save046C_v2/database.sqlite --output output/task03c-final-primary --seed task03c-final-a-fixed-v1
python tools/verify_season.py output/task03c-final-primary --reference docs/validation/task03c_season.json
```

The primary full-world fingerprint is
`399f8beef50aaf88aa740a283096e32aca2e06e61fc705be80f5e4504348ee48`.
Its complete journal reverses to exact accepted 046C; standings, aggregates,
receipts, native results, player statistics and financial deltas reconcile.
All 16 first-kickoff commitments survive an injected post-result crash; cached
results are reused. The sole inherited rest exception is Coritiba
`league:382 → league:393`, 69 hours. Known competition reservations introduce no
other sub-72-hour interval. Foreign domestic calendars/routes remain unknown.

The final secondary command uses `output/task03c-final-secondary` and seed
`task03c-final-b-fixed-v1`, providing a different injury/card/qualification path.
Its final fingerprint is `14a42de00d1a5b4e5643b8f7f3b545e9de3084f9576332b517bf8bf8aa975a51`. Both final scenarios completed all 217 fixtures and preserved 16 initial commitments through crash resumption. Private season reports include every match, champion, league table, payroll row
and state summary. Ordinary summaries intentionally omit future Vasco outcomes
and tables. `mirassol_preview.json` is produced at the actual pregame boundary
before executing that fixture in the disposable world.

## Portable persistence and independent restoration

The new `DEV-03C` profile remains nonpromotable. Complete input/result/events and
operation evidence stay in SQLite, so the compact portable payload does not
duplicate all execution/result/journal JSON in separate files. Hash-addressed
large row-image values are shared inside `world_blobs`; every reference is checked
against its exact canonical content. Journal reversal expands and verifies those
references. `world_draws` and `world_champions` are additive V2 structures; the
exact old table inventory, including historical `world_finals`, remains protected.

The primary DB is 83,759,104 bytes for 217 matches. Its portable payload retains
the unchanged format-1 100 MB extraction bound; no historical limit/baseline was
weakened. The manifest binds exact parent, policy, database and world hashes.
Export verifies the package and independently replays the whole season from a
fresh exact parent, then ZIP verification/restoration performs that check again.
Cursor positions are bound to result hashes and restored separately from football
state identity. Full-season archives and private diagnostic reports remain under
ignored `output/`, not accumulating Git binaries.

## Official-capable gate

`braga_era.forward` registers **`official-forward-profile-1`**, distinct from both
DEV profiles. Its lifecycle is prepare → signed batch authorization → immutable
execution/seed commitments → independently validated successor candidate → a
different exact-hash signed acceptance. The approval binds parent, engine/config,
proposed policy, seed namespace, exact chronological fixture slots and payroll
inventory. Fixture claims are unique across authorized batches for the same
parent, preventing a fresh execution ID/seed from generating competing outcomes
for an already authorized fixture. Process locks and SQLite transactions serialize
execution and acceptance; interrupted execution resumes its original directory.

An outer forward candidate binds the exact portable calculation archive, signed
authorization, receipts and world hash. Calculation payloads have their own
`FORWARD-CALCULATION-1` / `FORWARD-CALCULATION-TEST-1` identities and require an
authenticated scoped runtime. A DEV package cannot be renamed into this profile.
Pure engine calculation data stays unaccepted; only the distinct wrapper and a
separate commissioner decision can enter the forward acceptance registry.

Task 03C provisions **only disposable test registries**, simulated signing keys,
rehearsal candidates and test acceptance decisions. No production authority/key or
real accepted pointer is changed. The original `output/canonical.json` is not the
forward registry. A registry key grants trust; this is not a claim of independence
from someone who controls both code and the commissioner's key. The commissioner
must retain that authority outside the narrator's automatic decisions.

The initial profile pins accepted 046C. It supports specified remaining-2027
fixture slots without preassigning qualifiers, but is not an automatic migration
from any later accepted parent or a 2028 implementation. Later accepted-parent
profiles need their own reviewed registration; no arbitrary-parent bypass exists.

## Hikari interface and readiness judgment

`python -m braga_era.gameplay DIRECTORY next|preview|narrate|table|finances`
provides a practical local structured handoff. It gates previews/narration on the
earliest pending chronological group and reconstructs tables from revealed finals
only. Match events include halftime, ET and final whistles; final statistics unlock
only at the last event. Signed forward candidates use `forward.gameplay`, which
verifies their authority and reports candidate/accepted/test status. The
[operational runbook](official_play_runbook.md) includes the exact commands, runtime
requirements and interruption-safe conversational example.

The numerical [calibration report](task03c_calibration.md) and
[decision sheet](task03c_decisions.md) explicitly identify unresolved commissioner
choices. These include foreign quality priors, rare-event incidence/severity,
disciplinary resets, aggregate-aware coaching scope, neutral finals and draw
restrictions. Engineering consistency is demonstrated under the proposed rules;
empirical realism or commissioner acceptance is not implied. If different rules
are required, implement/version/verify them before authorizing an official batch.

Final validation status and artifact hashes are recorded in the validation evidence
alongside this report. No official-play readiness claim supersedes those checks
or the outstanding decisions. The recommended next task is commissioner review,
then a separately signed first batch covering September 30 and payroll only,
followed by independent restore and a separate successor acceptance decision.

## Local verification inventory

The unchanged baseline passed 197 tests; the expanded suite passed 207 tests in
469.76 seconds, followed by 11 readiness tests in 73.75 seconds after the additional
stage-draw recovery test. The final suite includes 210 tests, including explicit DEV-03C inspection and unsupported future-season rejection. Checks cover all
prior six execution crash stages, locks/concurrent runners, transaction rollback,
original/accepted hashes, tampered archives/history/journals, unsupported versions,
fitness/bans/contracts/identity, payroll idempotency, mixed neutral/nonneutral
commitments, committed-draw recovery, ET GK injury/dismissal, penalty eligibility,
signed batch/acceptance decisions, overlapping authorization claims and narration
spoiler/cursor corruption. The CI matrix additionally executes the complete golden
season on Windows/Linux 3.11-3.13, with a full-season archive round trip on Linux
3.12. Final job results are linked from the Task 03C PR and validation summary.

Foundation commands also passed: original bootstrap, default accepted inspect and
audit, strict 046C audit against original parent, and accepted ZIP verification.
Hash rechecks preserve original ZIP/DB, accepted ZIP/DB, approval receipt and the
real canonical registry. Development September payroll is R$1,799,666.67 at full
month end (the accepted September 26 accrual remains R$1,559,000.01 in its immutable
source); October-December are R$1,805,000 each under existing contracts. The test
account closes at R$23,335,333.33, above the unchanged R$16m reserve; no authority
budget, capital, award or revenue is invented.

## Portable artifact inventory

Final primary archive: `output/task03c-final-primary.zip`, SHA256
`d283775188e324db636606a628543f3ca766ab790beb0fa312cd694eb581ee8a`,
11,468,311 compressed bytes. Independent restoration at
`output/task03c-final-primary-restored` completed with full deterministic replay.
The ZIP is intentionally a local/CI artifact rather than a committed save binary.
The [verification inventory](validation/task03c_verification.json) records payload
size, protected hashes and test evidence. PR [#6](https://github.com/Lbragaa/FootballSimulatorStuff/pull/6)
remains open and unmerged. Cross-platform final job results are recorded there.

The installed 0.6.0 wheel independently restored the full primary ZIP from an
outside working directory using Python `-S` and only the isolated installed
package on PYTHONPATH. The restored world fingerprint exactly matched the
primary. The 1,200-trial calibration was repeated and reproduced digest
`84ecb58ee9696f11353d6782d834d87561ad3d644b2b01112e2b6c0f39513052`.

Forward gameplay verifies a signed independent-validation attestation, exact
archive hash and current working-world fingerprint (excluding narration cursors).
It does not rerun a season for every narration page. Candidate creation, explicit
verification and promotion retain full restoration/replay. Tampering with the
working calculation is rejected before Hikari sees it, even if the original
archive remains intact. Candidate state and signed validation receipt are committed
atomically. The initial official profile rejects 2028/time-zone boundaries.

## Final verification pass

The final local suite passed **210 tests in 460.46 seconds** on Windows/Python
3.12.14. The first PR matrix, run
[40583274560](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40583274560),
passed all six jobs at implementation commit
`3b939c16863422d1f6d69752bcdc76c405287152`: 208 tests per job, both old regulation
regressions, the unchanged Task 03B demo, and the 217-match golden season on every
OS/Python combination. Linux 3.12 also passed the complete season archive's full
independent restore/replay. The final additional authorization/delivery hardening
has 210 local tests; its matrix is tracked by the current PR head checks.
