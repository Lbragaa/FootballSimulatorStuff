# Task 02B — revised administrative checkpoint

**Accepted canonical state remains Save 046. Revised 046C v2 is a candidate only.** No matches were simulated, no current fictional date advanced, no engine implemented, and no canonical promotion occurred. Original ZIP/database/baseline and rejected v1 artifacts remain unchanged.

## GitHub publication and history

The requested original Phase 1 commit [abbf7f8](https://github.com/Lbragaa/FootballSimulatorStuff/commit/abbf7f86fcf1a0e0ec84ffa6223136758814d9e6) and both prior branches were verified published without force pushes or history rewriting. The ancestry is main `b229864` → Phase 0 `732c3ef` → Phase 1 `abbf7f8`, one commit per step.

- [PR #1: Phase 0 → main](https://github.com/Lbragaa/FootballSimulatorStuff/pull/1).
- [PR #2: Phase 1 → Phase 0](https://github.com/Lbragaa/FootballSimulatorStuff/pull/2).
- Task 02B is isolated on `codex/phase-1-calendar-finalize`, stacked on Phase 1. Its PR and CI outcome are recorded in the follow-up CI evidence file once published. Nothing is merged automatically.

Original PR CI passed: [Phase 0 run 40100351558](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40100351558) and [Phase 1 run 40100367611](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40100367611), Linux/Windows with Python 3.11–3.13. Revised-branch CI is pending publication at this report checkpoint; no pending result is claimed as a pass.

## Calendar comparison and recommendation

All primary strategies keep a hard minimum **72h kickoff-to-kickoff**, maximum three games in rolling eight days, **14-day maximum return-leg interval**, December 22–January 5 blackout, original completed history, and pinned Mirassol–Vasco on October 3 at 16:00. To avoid simply deferring every overdue tie into winter, known opening legs are constrained to start within 35 days. Future undrawn rounds reserve all possible qualifiers and never invent pairings or winners. The hourly grid is 16:00–22:00.

| Strategy | Outcome | League kickoff changes | Cup completion | Maximum stage wait | Realism heuristic |
|---|---|---:|---|---:|---:|
| A: cup-only | No feasible witness in the disclosed model | 0 | — | — | Unscored: hard constraints fail |
| B: controlled league adjustment | Feasible within modeled scope | 70 | 2027-12-21 16:00 | 28.00 days | 77.53/100 |
| C: exceptional 2028 postseason | Feasible within modeled scope | 0 | 2028-01-15 22:00 | 80.25 days | 66.37/100 |

**Recommend B.** A balanced congestion-window family followed by deterministic restoration of original dates reduces 116 initial kickoff changes to **70**: **36 calendar dates and 34 time-only changes**. It preserves the season boundary, avoids all holidays and reduces the longest interstage wait to 28 days. The 2028 option preserves league dates but extends final competition activity to January 15 and leaves an 80.25-day maximum stage wait, with preseason/contract/registration/finance consequences. The recommendation favors continuity and preserving the season, not merely earliest completion.

Recommended finals: **Copa do Brasil December 4, Libertadores December 7, Sudamericana December 21, all 16:00**. Return legs are three to seven days apart. Every completed fixture remains unchanged. Vasco's next match is pinned; its only later date changes are Fluminense–Vasco R28 (Oct17 → Oct18 16:00) and Athletico-PR–Vasco R38 (Dec19 → Dec18 16:00).

The score is an inspectable planning heuristic, not a calibrated probability or an assertion of global optimality. Weights: stability .20, congestion .20, travel .15, return-leg spacing .10, duration .10, holiday compliance .10, stage continuity .15. Components/formulas and complete A/B/C plans are in [comparison evidence](validation/task02b_alternatives.json) and `calendar_v2.py`. Hard-invalid schedules receive no score. Model infeasibility does not prove that every possible independently rearranged calendar is impossible; B's restored fixture count is not a proven global minimum.

An additional A sensitivity removed the 35-day opening-urgency bound (90-day allowance) and still emptied a legal date domain under the disclosed holiday/rest/return-leg model. Thus the reported A failure is not solely caused by the urgency assumption. Shorter C horizons were also explored: January 14 exhausted a bounded search (unproven), January 15–21 and January 31 yielded feasible witnesses; this report compares the January 15 witness, not a claimed mathematically earliest postseason finish.

Travel is explicitly scoped: 72h includes travel, matching the established kickoff-turnaround rule; it is never reduced below 72h. The default comparison adds no fabricated itinerary time. The same balanced family fails if six extra hours are imposed around continental events; that sensitivity is rejected rather than silently weakening the requested buffer. Foreign domestic calendars and actual routes/venues remain unavailable. Stronger recovery-after-travel requirements need a new proposal.

Inherited violations are distinguished by the exact original club/event pair and unchanged kickoffs. The recommendation removes 11 of the 12 inherited shortfalls, leaves **one** unchanged and introduces **zero** new shortfalls. Full interval/workload evidence is in [calendar validation](validation/save046c_v2_calendar.json).

## Revised candidate and checksums

Local review directory: `output/Save046C_v2/`. Portable archive: `output/Save046C_v2_candidate.zip`. It was restored independently into `output/restored-046C-v2/` and verified. Creation defaults to revision v2; original `output/Save046C/` and `output/Save046C_candidate.zip` are preserved rejected v1. Both can be verified archivally; v1 is unpromotable. No real registry pointer is created. [Proposal registry](validation/proposal_registry.json) is a human-readable inventory, not canonical acceptance.

- original_zip: `527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719`
- original_046_db: `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28`
- rejected_v1_db: `b87e672369e77879394c8ba373253cd12626ae2aad55fbe44862189ae0c0313a`
- rejected_v1_zip: `b8d050e50d952ff20f0c5037016a081459a1515deeb05156ec9e9b11d0a53668`
- revised_v2_db: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`
- revised_v2_zip: `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`
- permanent_046_baseline: `589395c70c52eda1924dbdab9be9b6f5a40d3b34f37cda5323c0df68d8178c23`
- original_v1_plan: `42571bd749f2b6ffbe925c7eb9a16d9b1be446306260eb9123607c307d42da2d`
- revised_v2_plan: `4eddc87409edce01b0cc518177a5c38019ae28e760f62436baacce1f58ba4d7a`

## Exact administrative and financial evidence

Schema version stays 1 because the seven additive table definitions are unchanged; the explicit migration ID `046_to_046C_admin_v2` and plan hash distinguish the revision. V2 independently replays all tables, protects 55 full original tables and every column of all 331 completed fixture rows, and permits only the exact logged future kickoff changes. All identities, transfers, sporting events and original results remain protected.

There are 189 operation records and 378 keyed row changes including the operation-log rows. [Complete before/after inventory](validation/save046c_v2_changes.json), [metadata](validation/save046c_v2_metadata.json), [audit](validation/save046c_v2_audit.json) and [finance](validation/save046c_v2_finance.json) are checked-in text evidence. Generated databases and accumulating ZIPs remain ignored. Storage/restoration strategy remains in [checkpoint protocol](checkpoints.md).

| Table | Changed/inserted keyed rows |
|---|---:|
| admin_operations | 189 |
| admin_policies | 2 |
| board_objectives | 4 |
| calendar_events | 57 |
| cdb_2027_bracket | 7 |
| cdb_2027_plan_meta | 2 |
| checkpoint_info | 1 |
| finance_ledger | 1 |
| fixtures | 70 |
| libertadores_2027_meta | 1 |
| libertadores_2027_round_of_16 | 8 |
| meta | 10 |
| payroll_obligations | 8 |
| payroll_periods | 9 |
| schema_migrations | 1 |
| sudamericana_2027_playoffs | 8 |

The financial policy remains exactly the provisionally supported direction: August paid once R$1.38m; cash R$30.55m; September accrued R$1,559,000.01, no September cash; month-end posting, contract-start proration, per-player cent rounding, unchanged annual commitments and R$16m reserve. Five per-player obligations reconcile to R$1,799,666.67 full September service and R$1,559,000.01 accrued through Sep26. No untracked base salaries or capital is added. Carioca/CDB objectives achieved, Sudamericana failed, league/youth/season-wide Finance pending; R$68m authority wording retained.

## Tests and remaining decisions

Local Windows/Python 3.12.14/pytest 9.1.1: **95 tests passed in 91.92s**. Revised audit: **36 checks, zero failures, 10 explicit warnings**. Coverage includes both immutable baseline/archived-v1 regressions, A/B/C deterministic comparison, hard holiday and rest floor, leg bounds, protected Mirassol/completed fixtures, controlled kickoff tampering, player-level accruals, rollback including future league moves, duplicate payroll, no-overwrite lifecycle, deterministic manifests and independent restoration. Temporary promotion tests never touch a real canonical registry.

Version 0.3.0 was installed in the project environment and built into a normal wheel offline. An isolated wheel installation outside the checkout verified both the rejected v1 archive (not acceptance-eligible) and revised v2 archive (integrity-valid, awaiting explicit acceptance), including packaged baseline and both plan revisions.

Commissioner decisions still required:

1. Accept or revise the full **70-kickoff inventory** and the two later Vasco date changes. Mirassol–Vasco October 3 is unchanged.
2. Accept the disclosed **72h total-turnaround/travel scope and one untouched inherited exception**, acknowledging missing foreign calendars/itineraries; request a new solve if stronger recovery constraints are required.
3. Accept the exact v2 candidate hash with its provisionally supported accounting direction. That future acceptance is separate from the engineering PRs and would still not authorize R26 automatically.

No holiday exception or 2028 postseason authorization is required by recommended B. If C is chosen instead, explicitly decide season labels vs event dates, contract/registration eligibility after Dec31, preseason/2028 competition overlap, and financial authority/accruals; no season rollover, contract renewal or new capital has been assumed.

## Proposed Phase 2 milestones

[Detailed headless engine design](phase2_engine_design.md) specifies legacy mechanics and a clean interface for pregame snapshots, eligibility/autonomous lineups, versioned configuration/seeds, pure single-match results, exact chronological narration events, one-time official execution receipts, scratch transactional persistence, audits, portable exports and separate noncanonical Monte Carlo forecasts.

Milestones: (1) typed contracts/read-only adapters and legacy characterization; (2) pure deterministic match core and event validation; (3) autonomous coach policy; (4) receipt/claim persistence and crash-safe round/cup adapters; (5) spoiler-safe narration/export and forecast isolation; (6) commissioner review before any official execution. The September 30 continental legs precede R26 in the recommended agenda and must not be silently skipped. No engine was implemented in this task.

---

# Revised Save 046C — proposal v2, not accepted

Fictional date remains 2027-09-26 23:30. No matches simulated, no R26, no canonical promotion.
Database SHA256: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`. Parent: `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28`.
Original holiday proposal v1 is preserved separately and explicitly rejected by Task 02B.

## Recommended strategy B: controlled league adjustment

All cups finish in 2027; December 22–January 5 is a hard blackout. Mirassol–Vasco on October 3 at 16:00 is unchanged.
70 scheduled kickoffs change: 36 calendar dates and 34 times only. No completed fixture changes. Comparison heuristic score: 77.53/100.
Return legs span at most 7.00 days; minimum new kickoff turnaround 72h. Maximum workload 3 in eight days.
One inherited rest exception remains; no new shortfalls. Maximum interstage wait: 28.0 days. These are conservative potential-qualifier reservations, not assumed winners.

| Known tie or provisional reservation | Leg | Original date | Proposed kickoff | Entry type |
|---|---:|---|---|---|
| LIB-R16-01:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-02:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-03:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-04:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-05:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-06:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-07:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| LIB-R16-08:L1 | 1 | 2027-08-31 | 2027-09-30 16:00 | known fixture |
| SULA-PO-01:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-02:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-03:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-04:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-05:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-06:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-07:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| SULA-PO-08:L1 | 1 | 2027-08-26 | 2027-09-30 16:00 | known fixture |
| LIB-R16-01:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-02:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-03:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-04:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-05:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-06:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-07:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| LIB-R16-08:L2 | 2 | 2027-09-07 | 2027-10-06 16:00 | known fixture |
| SULA-PO-01:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-02:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-03:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-04:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-05:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-06:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-07:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| SULA-PO-08:L2 | 2 | 2027-09-02 | 2027-10-06 16:00 | known fixture |
| CDB:QF-01:L1 | 1 | 2027-09-15 | 2027-10-12 16:00 | known fixture |
| CDB:QF-02:L1 | 1 | 2027-09-15 | 2027-10-12 16:00 | known fixture |
| CDB:QF-03:L1 | 1 | 2027-09-15 | 2027-10-12 16:00 | known fixture |
| CDB:QF-04:L1 | 1 | 2027-09-15 | 2027-10-12 16:00 | known fixture |
| CDB:QF-01:L2 | 2 | 2027-09-22 | 2027-10-15 16:00 | known fixture |
| CDB:QF-02:L2 | 2 | 2027-09-22 | 2027-10-15 16:00 | known fixture |
| CDB:QF-03:L2 | 2 | 2027-09-22 | 2027-10-15 16:00 | known fixture |
| CDB:QF-04:L2 | 2 | 2027-09-22 | 2027-10-15 16:00 | known fixture |
| reserve:LIB:QF:L1 | 1 | undrawn | 2027-10-21 16:00 | provisional reservation |
| reserve:SULA:R16:L1 | 1 | undrawn | 2027-10-21 16:00 | provisional reservation |
| reserve:LIB:QF:L2 | 2 | undrawn | 2027-10-27 16:00 | provisional reservation |
| reserve:SULA:R16:L2 | 2 | undrawn | 2027-10-27 16:00 | provisional reservation |
| CDB:SF-01:L1 | 1 | 2027-10-13 | 2027-11-09 16:00 | provisional reservation |
| CDB:SF-02:L1 | 1 | 2027-10-13 | 2027-11-09 16:00 | provisional reservation |
| CDB:SF-01:L2 | 2 | 2027-10-20 | 2027-11-12 16:00 | provisional reservation |
| CDB:SF-02:L2 | 2 | 2027-10-20 | 2027-11-12 16:00 | provisional reservation |
| reserve:LIB:SF:L1 | 1 | undrawn | 2027-11-24 16:00 | provisional reservation |
| reserve:SULA:QF:L1 | 1 | undrawn | 2027-11-24 16:00 | provisional reservation |
| reserve:LIB:SF:L2 | 2 | undrawn | 2027-12-01 16:00 | provisional reservation |
| reserve:SULA:QF:L2 | 2 | undrawn | 2027-12-01 16:00 | provisional reservation |
| CDB:FINAL-01:L1 | 1 | 2027-12-05 | 2027-12-04 16:00 | provisional reservation |
| reserve:LIB:FINAL:L1 | 1 | undrawn | 2027-12-07 16:00 | provisional reservation |
| reserve:SULA:SF:L1 | 1 | undrawn | 2027-12-07 16:00 | provisional reservation |
| reserve:SULA:SF:L2 | 2 | undrawn | 2027-12-14 16:00 | provisional reservation |
| reserve:SULA:FINAL:L1 | 1 | undrawn | 2027-12-21 16:00 | provisional reservation |

## Every league kickoff adjustment

| Fixture ID | Original kickoff | Proposed kickoff |
|---:|---|---|
| 333 | 2027-10-02 16:00 | 2027-10-03 16:00 |
| 334 | 2027-10-02 18:00 | 2027-10-03 16:00 |
| 335 | 2027-10-02 20:00 | 2027-10-03 16:00 |
| 336 | 2027-10-03 17:00 | 2027-10-03 16:00 |
| 339 | 2027-10-03 20:00 | 2027-10-03 16:00 |
| 341 | 2027-10-03 17:00 | 2027-10-03 16:00 |
| 344 | 2027-10-09 18:00 | 2027-10-09 16:00 |
| 345 | 2027-10-09 20:00 | 2027-10-09 16:00 |
| 349 | 2027-10-10 20:00 | 2027-10-09 16:00 |
| 350 | 2027-10-10 16:00 | 2027-10-09 16:00 |
| 351 | 2027-10-10 17:00 | 2027-10-09 16:00 |
| 352 | 2027-10-17 16:00 | 2027-10-18 16:00 |
| 353 | 2027-10-17 17:00 | 2027-10-18 16:00 |
| 354 | 2027-10-17 18:00 | 2027-10-18 16:00 |
| 355 | 2027-10-17 19:00 | 2027-10-18 16:00 |
| 359 | 2027-10-17 18:00 | 2027-10-18 16:00 |
| 360 | 2027-10-17 19:00 | 2027-10-18 16:00 |
| 361 | 2027-10-17 20:00 | 2027-10-18 16:00 |
| 363 | 2027-10-24 17:00 | 2027-10-24 16:00 |
| 366 | 2027-10-24 19:00 | 2027-10-24 16:00 |
| 367 | 2027-10-24 20:00 | 2027-10-24 16:00 |
| 369 | 2027-10-24 17:00 | 2027-10-24 16:00 |
| 370 | 2027-10-24 18:00 | 2027-10-24 16:00 |
| 371 | 2027-10-24 19:00 | 2027-10-24 16:00 |
| 376 | 2027-10-31 17:00 | 2027-10-31 16:00 |
| 377 | 2027-10-31 18:00 | 2027-10-31 16:00 |
| 378 | 2027-10-31 19:00 | 2027-10-31 16:00 |
| 379 | 2027-10-31 20:00 | 2027-10-31 16:00 |
| 381 | 2027-10-31 17:00 | 2027-10-31 16:00 |
| 383 | 2027-11-03 19:30 | 2027-11-03 16:00 |
| 384 | 2027-11-03 20:00 | 2027-11-03 16:00 |
| 385 | 2027-11-03 20:30 | 2027-11-03 16:00 |
| 386 | 2027-11-03 21:00 | 2027-11-03 16:00 |
| 387 | 2027-11-03 19:00 | 2027-11-03 16:00 |
| 388 | 2027-11-03 19:30 | 2027-11-03 16:00 |
| 389 | 2027-11-03 20:00 | 2027-11-03 16:00 |
| 390 | 2027-11-03 20:30 | 2027-11-03 16:00 |
| 394 | 2027-11-06 18:00 | 2027-11-06 16:00 |
| 395 | 2027-11-06 20:00 | 2027-11-06 16:00 |
| 396 | 2027-11-07 17:00 | 2027-11-06 16:00 |
| 398 | 2027-11-07 19:00 | 2027-11-06 16:00 |
| 399 | 2027-11-07 20:00 | 2027-11-06 16:00 |
| 404 | 2027-11-13 18:00 | 2027-11-15 16:00 |
| 405 | 2027-11-13 20:00 | 2027-11-15 16:00 |
| 406 | 2027-11-14 17:00 | 2027-11-15 16:00 |
| 407 | 2027-11-14 18:00 | 2027-11-15 16:00 |
| 408 | 2027-11-14 19:00 | 2027-11-15 16:00 |
| 410 | 2027-11-14 16:00 | 2027-11-15 16:00 |
| 413 | 2027-11-17 19:30 | 2027-11-18 16:00 |
| 414 | 2027-11-17 20:00 | 2027-11-18 16:00 |
| 415 | 2027-11-17 20:30 | 2027-11-18 16:00 |
| 416 | 2027-11-17 21:00 | 2027-11-18 16:00 |
| 417 | 2027-11-17 19:00 | 2027-11-18 16:00 |
| 418 | 2027-11-17 19:30 | 2027-11-18 16:00 |
| 419 | 2027-11-17 20:00 | 2027-11-18 16:00 |
| 421 | 2027-11-17 21:00 | 2027-11-18 16:00 |
| 423 | 2027-11-20 16:00 | 2027-11-21 16:00 |
| 424 | 2027-11-20 18:00 | 2027-11-21 16:00 |
| 425 | 2027-11-20 20:00 | 2027-11-21 16:00 |
| 428 | 2027-11-21 19:00 | 2027-11-21 16:00 |
| 429 | 2027-11-21 20:00 | 2027-11-21 16:00 |
| 431 | 2027-11-21 17:00 | 2027-11-21 16:00 |
| 437 | 2027-11-28 18:00 | 2027-11-28 16:00 |
| 439 | 2027-11-28 20:00 | 2027-11-28 16:00 |
| 444 | 2027-12-11 18:00 | 2027-12-11 16:00 |
| 445 | 2027-12-11 20:00 | 2027-12-11 16:00 |
| 446 | 2027-12-12 17:00 | 2027-12-11 16:00 |
| 452 | 2027-12-19 16:00 | 2027-12-18 16:00 |
| 455 | 2027-12-18 20:00 | 2027-12-18 16:00 |
| 456 | 2027-12-19 17:00 | 2027-12-18 16:00 |

Vasco changes only: Fluminense–Vasco R28, October 17 → October 18 at 16:00; Athletico-PR–Vasco R38, December 19 → December 18 at 16:00. R26 Mirassol–Vasco is pinned.

## Finance and board evidence

August: R$1,380,000 paid once. Restricted cash: R$31,930,000 → R$30,550,000. September cash: zero; accrued liability R$1,559,000.01; full-month obligation R$1,799,666.67. Actual-day proration and per-player cent rounding apply. No untracked base payroll, new capital or duplicate annual commitment debit.
Annual incremental commitments R$21.66m; wage headroom R$0.34m; fee authority remaining R$1.4m; agents/scouting remaining R$2.19m; restricted emergency reserve R$16m unchanged.

| Player ID | Monthly BRL | September due BRL | Accrued through Sep26 BRL |
|---:|---:|---:|---:|
| 163 | 430,000.00 | 430,000.00 | 372,666.67 |
| 227 | 265,000.00 | 265,000.00 | 229,666.67 |
| 304 | 160,000.00 | 154,666.67 | 133,333.33 |
| 384 | 310,000.00 | 310,000.00 | 268,666.67 |
| 401 | 640,000.00 | 640,000.00 | 554,666.67 |

Carioca/Copa do Brasil objectives achieved; Sudamericana failed. League/youth/season-wide Finance stay pending. R$68m fee wording retained.

## Remaining commissioner decisions

Accept or revise the complete 70-kickoff inventory, the 72h total-turnaround/travel scope and the one preserved original shortfall. Finance direction is supported for preparing this candidate, not automatic promotion. No 2028 extension is needed for the recommendation; the scored alternative requires separate postseason, registration/contracts, preseason and finance policy decisions.
Unknown foreign domestic commitments and actual routes/venues prevent a global-calendar guarantee. No rest rule is weakened below 72h; any stronger travel-plus-recovery requirement needs a new solve. Scores are transparent planning heuristics, not calibrated sport probabilities.

Operations: 189 logged keyed changes; complete changes.json includes those log rows too. Changed tables: admin_operations, admin_policies, board_objectives, calendar_events, cdb_2027_bracket, cdb_2027_plan_meta, checkpoint_info, finance_ledger, fixtures, libertadores_2027_meta, libertadores_2027_round_of_16, meta, payroll_obligations, payroll_periods, schema_migrations, sudamericana_2027_playoffs.

## Validation

36 checks, 0 failures, 10 warnings.
- PASS [v2.parent]: Original Save 046 and permanent baseline authenticated independently
- PASS [sqlite.integrity]: SQLite integrity
- PASS [sqlite.foreign_keys]: Declared foreign keys
- PASS [v2.calendar]: Holiday blackout, bounded legs, confirmed pairings, conditional reservations, rest/workload and league order checked
- PASS [v2.schema]: Exact explicit administrative schema
- PASS [v2.table_inventory]: Original tables retained and seven administrative tables added
- PASS [v2.historical_tables]: All 55 untouched original tables preserved, including players/attribution/events/transfers; drift: []
- PASS [v2.completed_fixtures]: All 331 completed fixture rows unchanged in every column
- PASS [v2.authorized_delta]: Every table equals independent replay, including exact permitted scheduled kickoff changes; drift: []
- PASS [v2.provenance]: Version, v2 revision, parent, plan and unaccepted status
- PASS [v2.finance]: August R$1.38m settled once; cash R$30.55m; September liability R$1,559,000.01, no September cash
- PASS [v2.player_payroll]: September due/accrued obligations reconcile per player under actual-day and per-player cent rounding
- PASS [v2.periods]: Nine unique obligation periods; eight unique cash ledger links
- PASS [v2.holidays]: No new or moved match during December 22-January 5
- PASS [v2.rest]: No newly introduced sub-72h interval; inherited exceptions identified by exact original pair and kickoffs
- PASS [save046c.meta]: Save 046C date, next fixture, confidence and manager counter match
- PASS [league.participants]: 20 distinct 2027 league clubs
- PASS [league.inventory]: 380 league fixtures: 250 final, 130 scheduled
- PASS [league.rounds]: 38 ten-game rounds; each club appears once per round
- PASS [league.pairings]: Every ordered home-away pairing occurs once
- PASS [league.future_unplayed]: Scheduled league matches have no scores
- PASS [league.standings]: All 20 standings recomputed from results
- PASS [vasco.standings]: Vasco ninth: 38 pts, 25 played, 11W 5D 9L, 36-37
- PASS [vasco.palmeiras]: Vasco 3-2 Palmeiras is final, once
- PASS [vasco.next]: Mirassol-Vasco, October 3 at 16:00, R26 remains unplayed
- PASS [r25.events]: R25 goals, shots, xG and 22 starters reconcile; mismatches: []
- PASS [r25.rojas_order]: Johan Rojas enters before his 82nd-minute winner in database event order
- PASS [players.identities]: Archived Savarino #196 and active #354 retained as separate identities
- PASS [inventory.players]: players: 547 records
- PASS [inventory.transfers]: transfers: 9 records
- PASS [inventory.archive2026]: archive2026: 20 records
- PASS [inventory.libertadores.groups]: libertadores.groups: 96 records
- PASS [inventory.sudamericana.groups]: sudamericana.groups: 96 records
- PASS [inventory.cdb.legs]: cdb.legs: 48 records
- PASS [finance.cash]: Restricted ledger cash R$30,550,000
- PASS [finance.authority]: Acquisition, annual wage, agent headroom and reserved funds match approved budgets
- WARN [known.2026]: 2026 final standings archived, granular fixtures partial (71 league records); do not reconstruct missing results
- WARN [known.dates]: 39 completed fixtures lack an ISO calendar date; preserve unknowns
- WARN [known.cards]: 22 historical cards occur after the starter's recorded exit minute; no retrospective event edits
- WARN [known.engine_metrics]: 169 engine-audit rows have both prematch xG fields empty/zero; historical reproducibility limited
- WARN [known.identity]: Savarino #196 archive and active #354 both currently reference Fluminense club_id=5; use identity resolution for eligibility
- WARN [known.legacy_code]: Reference engine and episode scripts contain top-level writes, absolute paths, text replacement and exec; inspected only, never imported or executed
- WARN [known.json_order]: results046.json sorts Rojas GOAL before SUBSTITUTION at minute 82; database IDs and episode correctly place substitution first
- WARN [v2.calendar_review]: 70 future kickoffs change (36 matchdays, 34 time only); Mirassol-Vasco pinned; 1 inherited league exception remains
- WARN [v2.travel_scope]: 72h is kickoff-to-kickoff including travel; six extra hours are a sensitivity scenario, not hidden relaxation; foreign schedules/itineraries remain unknown
- WARN [v2.acceptance]: Payroll direction provisionally supported for candidate preparation; full candidate acceptance and R26 require subsequent authorization
