# Development roadmap

Current status after Task 03B: exact 046C v2 accepted administratively, PRs #1–#4 merged, a working regulation engine plus chronological multi-competition development world, proposed foreign squads, player-state persistence and restorable DEV-03B packages delivered. No official play or time advance. [Task 03B report](task03b_report.md) and [Task 03C plan](task03c_plan.md) define the current boundary. The phase descriptions below retain the original administrative development sequence; pending-acceptance language describes the earlier Task 02B stage.

## Phase 0 — protected foundation (implemented)

Authenticated extraction, preserved original backups, read-only SQL access, package and CLI, stable historical snapshot/table hashes, structured audit results, automated tests and documentation. No match execution, calendar progression or writable checkpoint management.

## Phase 1 — administrative Save 046C (candidate implemented, not accepted)

Task 02B supersedes the rejected holiday calendar with candidate v2: controlled future league adjustment, all cups finished by December 21, a hard holiday blackout, bounded return legs and no newly introduced rest violations. The old proposal remains immutable and unpromotable. Stacked engineering PRs preserve the commit chain; acceptance of the revised save remains separate. [Task 02B report](task02b_report.md) and [next engine design](phase2_engine_design.md) define the current review boundary.

Candidate creation, transactional reconciliation, explicit revision-aware 046C replay validation, verified export/restore and a separate acceptance API are implemented. Revised v2 needs acceptance of the exact future kickoff inventory and rest/travel scope; its accounting directions are provisionally supported for preparation. No holiday scheduling exception or 2028 extension is part of the recommendation. No game or fictional date has advanced. The implementation scope below is delivered as an unaccepted candidate.

Start from an authenticated **copy** of Save 046 and produce a separately versioned candidate. Keep parent SHA256, schema/profile version, operation log and output hash; validate candidate and retain parent before promoting any new canonical pointer.

1. Inventory overdue 8/8/4 cup ties and remaining season commitments. Reschedule unfinished ties to feasible future slots, respecting leg order, rest/travel and league conflicts; log each old date, new date and reason. Include downstream rounds/finals and reject impossible schedules. No match simulation, retrospective fitness effects or invented results in the administrative checkpoint.
2. Reconcile August incremental payroll from actual contracts and recognized ledger entries. Define September due-date/proration policy including Arthur Dias (R$265k/month) and Barreal (R$160k/month); distinguish cash, accrued obligations, annual commitments and category authority. Add idempotent period keys and a reconciliation report. Avoid charging unspecified historical base payroll.
3. Reconcile settled Carioca/CDB/Sudamericana objective flags with SQL evidence, and update obsolete budget wording/metadata against recorded capital authorization. Preserve league/youth objectives that remain unresolved.
4. Add minimal, documented administrative schema migrations/logs only as needed; no changes to previously completed fixtures, events, transfers, identity history or 2026 archive. Add a 046C validation profile that permits only reviewed administrative deltas and retains the frozen 046 historical baseline.
5. Validate FK/integrity, collision detection, payroll idempotency, budget arithmetic and all historical hashes on independent test copies. Package 046C with database, parent provenance, manifest and reconciliation narrative, then test restoration to both 046 and 046C in isolated directories.

Acceptance: every overdue tie is transparently accounted for, all debits have evidence and unique period identity, no settled sporting result changes, no fictional time advancement by side effect, and no R26 execution. A separate request authorizes future gameplay.

## Phase 2 — modular forward-only match engine

Design explicit state/configuration, roster eligibility, autonomous coach selection, tactics, form, bounded training/chemistry effects, xG/chances, fitness, injuries, substitutions and event sequence. Keep seed/configuration/engine version and input snapshot precommitted; run each official match exactly once. Validate on-field eligibility, score/shot/event/player accounting, standings and persistence before transactional save promotion. Support deterministic replay on isolated copies for verification without replacing official outcomes. Never tune a finished result. Deliver chronological structured events for narration with outcome information held until the final whistle.

## Phase 3 — optional Streamlit universe dashboard

Read-only views for every club/player, competitions, history, fixtures, tactics, transfers, budgets, provenance and audit warnings. Make known missing data visible. Keep analytical forecasts separate from official results. No dashboard dependency belongs in the core engine until this phase is requested.

## Phase 4 — long-term football ecosystem

Season rollover for 2028+, competition qualification/brackets, promotions/relegations, youth and aging progression, contracts/transfers, autonomous clubs/managers, sponsorship/attendance and restricted finance, coaching career history and slowly evolving tactical units. Add domain-specific migration/version policies, bounded forecasts, reproducible long-run tests and restorable versioned saves. Preserve earlier universe history across every new season.
