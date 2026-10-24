# Phase 1 implementation and candidate delivery

Historical delivery record: Task 02B rejected this v1 calendar. Its database, ZIP and original profile remain unchanged for archival verification. See [revised Task 02B report](task02b_report.md) for candidate v2; neither proposal is accepted canonical state.

Branch: `codex/phase-1-admin-046c`. Save **046 remains the accepted canonical state**. Candidate 046C has not been promoted; the fictional date remains 2027-09-26 23:30 and Mirassol-Vasco R26 remains scheduled/unplayed. No replacement engine or dashboard was implemented.

The delivery includes working candidate lifecycle/restore infrastructure, centralized deterministic calendar reconciliation, contract-backed incremental payroll and separate accrued liabilities, objective/metadata cleanup, the explicit 046C replay audit, regression tests and updated documentation. The frozen 046 baseline is unchanged. The original ZIP and database retain their original hashes.

Local candidate: `output/Save046C/`. Portable review artifact: `output/Save046C_candidate.zip`. Parent-only backup: `output/Save046_parent.zip`. Both ZIPs were restored and verified independently into new output directories. The output directory is ignored, and no generated database/ZIP is committed.

## Actual validation and CI status

- Windows, Python 3.12.14, pytest 9.1.1: **73 passed in 45.30 seconds**.
- Original 046 profile: preserved, with its known inherited warnings; original baseline/history tests still pass.
- Candidate 046C: **32 checks, zero failures, 10 warnings** (seven retained historical quality warnings and three policy/calendar review warnings).
- Regression coverage includes deterministic reconciliation and ZIP bytes; collision/unsatisfiable calendar scenarios; wrong parent and unsupported version rejection; duplicate, early and reserve-consuming payroll attempts; all-stage failure rollback; nine unauthorized history/admin/schema mutation scenarios; forged/resealed manifests and reports; path traversal; overwrite rejection; independent 046/046C restore; and explicit acceptance gates on temporary registries only.
- CLI creation, explicit 046C audit, export, ZIP verification and independent parent/candidate restore were executed successfully. No real canonical pointer was created.
- Version 0.2.0 was installed in the project environment. A normal wheel was built offline, installed in an isolated target, and successfully audited 046C and verified its ZIP from outside the checkout; the packaged profile module, 57-event plan and permanent baseline are present.
- GitHub Actions matrix is extended to test Python 3.11–3.13 on Linux/Windows and exercise candidate create/audit/export/restore. **Remote CI has not run; local Windows verification is the actual evidence.**

## Commands

From the configured environment, use the commands in [README](../README.md). This checkout can use `.\.venv\Scripts\python.exe` in place of `python`.

```sh
python -m pip install -e ".[dev]"
python -m braga_era inspect
python -m braga_era inspect --db output/Save046C/database.sqlite
python -m braga_era audit --profile 046C --db output/Save046C/database.sqlite --parent data/handoff/canonical/braga_save.sqlite
python -m braga_era save verify output/Save046C_candidate.zip
python -m braga_era save export output/Save046C --output output/a-new-archive-name.zip
python -m braga_era save restore output/Save046C_candidate.zip --output output/a-new-restore-directory
python -m pytest
```

Existing outputs cannot be overwritten. To create another identical candidate, use `save create --parent data/handoff/canonical/braga_save.sqlite --output output/NEW-NAME`. No promotion CLI exists. See [checkpoint protocol/storage](checkpoints.md) and [payroll policy](payroll_policy.md).

## Checksums

- original_handoff_zip: `527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719`
- original_046_database: `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28`
- candidate_046c_database: `b87e672369e77879394c8ba373253cd12626ae2aad55fbe44862189ae0c0313a`
- candidate_046c_zip: `b8d050e50d952ff20f0c5037016a081459a1515deeb05156ec9e9b11d0a53668`
- parent_046_zip: `db4b6c6a0b18bab0e58352f8efc83f8c66c8ac4172182ee609e685fac0f977ea`
- permanent_046_baseline: `589395c70c52eda1924dbdab9be9b6f5a40d3b34f37cda5323c0df68d8178c23`
- reviewed_046c_calendar_plan: `42571bd749f2b6ffbe925c7eb9a16d9b1be446306260eb9123607c307d42da2d`

## Exact row inventory

[Complete before/after row inventory](validation/save046c_changes.json) includes every application row and operation-log row. [Metadata](validation/save046c_metadata.json), [audit](validation/save046c_audit.json), [calendar/rest evidence](validation/save046c_calendar.json) and [finance](validation/save046c_finance.json) are checked-in text reports; the archive contains equivalent originals plus the operation log and full original parent database.

| Changed table | Changed/inserted keyed rows |
|---|---:|
| admin_operations | 119 |
| admin_policies | 2 |
| board_objectives | 4 |
| calendar_events | 57 |
| cdb_2027_bracket | 7 |
| cdb_2027_plan_meta | 2 |
| checkpoint_info | 1 |
| finance_ledger | 1 |
| libertadores_2027_meta | 1 |
| libertadores_2027_round_of_16 | 8 |
| meta | 10 |
| payroll_obligations | 8 |
| payroll_periods | 9 |
| schema_migrations | 1 |
| sudamericana_2027_playoffs | 8 |
| **Total** | **238** |

Eight original administrative tables change; seven new administrative tables are added. All **56 other original user tables**, including all fixtures/league dates, events, shots, performances, player identities, transfers, contracts, budgets and archived standings, retain their frozen original fingerprints. DDL is explicit and transactionally logged by migration ID/hash. Original columns and sporting rows are not rewritten.

## Commissioner decisions and alternatives

The candidate is technically validated under its proposed policy, with explicit unresolved constraints. It is **not an accepted canonical save** and is not a claim that every real-world/global football calendar constraint is known.

1. Accept or revise **72h kickoff-to-kickoff including travel**, the preserved 12 inherited fixed league shortfalls and three-match/eight-day workload cap. A 72h plus six-extra-travel-hours model has no solution in the conservative stage-wide 16:00–21:00 grid before year-end. Actual itineraries and foreign domestic matches are absent.
2. Accept or revise the **December 25 semifinals, December 28 continental finals, December 31 Copa final and long inter-leg gaps**. No tournament was moved into 2028. If stronger travel/recovery or holiday constraints are required, alternatives are explicit permission to retime unplayed league games, a separately authorized 2028 extension with season/contract/finance consequences, or later branch-aware refinement once actual qualifiers/draws exist. None is silently assumed or performed.
3. Accept or revise **actual-calendar-day, inclusive-start, per-player cent rounding and month-end incremental payroll**; preserve January–July simplifications, settle August once, and leave September as an accrued liability without advancing time. The untracked base payroll remains unknown.

Selected operational metadata is reconciled from structured evidence. Historical snapshot/checkpoint-specific narrative notes are retained as context and do not override current structured state. Future software should continue reading authoritative structured tables.

Phase 2 is ready for architecture/prototype engineering after review of this foundation. Official gameplay should wait for commissioner acceptance of the administrative policies/calendar and an explicitly authorized next phase. The replacement engine and R26 have not been executed.

---

# Save 046C — candidate

Fictional date: 2027-09-26 23:30. No matches simulated or clock advancement.
Database SHA256: `b87e672369e77879394c8ba373253cd12626ae2aad55fbe44862189ae0c0313a`.
Parent SHA256: `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28`.

Validation: 32 checks, 0 failures, 10 warnings.
Canonical pointer unchanged. Candidate production is separate from commissioner acceptance.

## Calendar feasibility

All new cup commitments pass the 72-hour kickoff-turnaround and rolling-workload model.
League fixtures are unchanged. This is conditional feasibility, not a claim that inherited league rest problems were repaired.
The stricter 72h + 6h travel model has no solution on the conservative stage-wide grid before year-end.
New rest intervals: `{'under_72': 0, '72_to_95': 219, '96_to_167': 47, '168_plus': 118}`; minimum 72.0h.
Inherited fixed league shortfalls: 12; minimum 68.0h.

| Tie / reservation | Stage | Leg | Old date | Proposed kickoff | Participants / potential qualifiers |
|---|---|---:|---|---|---|
| LIB-R16-06:L1 | R16 | 1 | 2027-08-31 | 2027-09-29 20:00 | Huachipato vs Flamengo |
| SULA-PO-08:L1 | PO | 1 | 2027-08-26 | 2027-09-30 17:00 | Newell's Old Boys vs Botafogo |
| LIB-R16-02:L1 | R16 | 1 | 2027-08-31 | 2027-10-06 16:00 | Junior de Barranquilla vs Fluminense |
| LIB-R16-01:L1 | R16 | 1 | 2027-08-31 | 2027-10-06 18:00 | Bolívar vs Palmeiras |
| LIB-R16-06:L2 | R16 | 2 | 2027-09-07 | 2027-10-06 18:00 | Flamengo vs Huachipato |
| LIB-R16-05:L1 | R16 | 1 | 2027-08-31 | 2027-10-06 20:00 | Estudiantes vs Santos |
| SULA-PO-04:L1 | PO | 1 | 2027-08-26 | 2027-10-07 16:00 | Athletico-PR vs Peñarol |
| SULA-PO-08:L2 | PO | 2 | 2027-09-02 | 2027-10-07 16:00 | Botafogo vs Newell's Old Boys |
| LIB-R16-04:L1 | R16 | 1 | 2027-08-31 | 2027-10-07 17:00 | Atlético-MG vs River Plate |
| SULA-PO-03:L1 | PO | 1 | 2027-08-26 | 2027-10-07 18:00 | Sporting Cristal vs São Paulo |
| SULA-PO-07:L1 | PO | 1 | 2027-08-26 | 2027-10-07 20:00 | Bragantino vs Independiente |
| LIB-R16-02:L2 | R16 | 2 | 2027-09-07 | 2027-10-14 16:00 | Fluminense vs Junior de Barranquilla |
| CDB:QF-03:L1 | Quartas | 1 | 2027-09-15 | 2027-10-14 17:00 | Flamengo vs Botafogo |
| SULA-PO-03:L2 | PO | 2 | 2027-09-02 | 2027-10-14 17:00 | São Paulo vs Sporting Cristal |
| SULA-PO-07:L2 | PO | 2 | 2027-09-02 | 2027-10-14 17:00 | Independiente vs Bragantino |
| LIB-R16-01:L2 | R16 | 2 | 2027-09-07 | 2027-10-14 19:00 | Palmeiras vs Bolívar |
| LIB-R16-04:L2 | R16 | 2 | 2027-09-07 | 2027-10-14 20:00 | River Plate vs Atlético-MG |
| LIB-R16-05:L2 | R16 | 2 | 2027-09-07 | 2027-10-14 20:00 | Santos vs Estudiantes |
| SULA-PO-04:L2 | PO | 2 | 2027-09-02 | 2027-10-14 20:00 | Peñarol vs Athletico-PR |
| LIB-R16-03:L1 | R16 | 1 | 2027-08-31 | 2027-10-15 16:00 | O'Higgins vs Vélez Sarsfield |
| LIB-R16-07:L1 | R16 | 1 | 2027-08-31 | 2027-10-15 16:00 | The Strongest vs Liverpool (URU) |
| LIB-R16-08:L1 | R16 | 1 | 2027-08-31 | 2027-10-15 16:00 | Atlético Nacional vs Sportivo Luqueño |
| SULA-PO-01:L1 | PO | 1 | 2027-08-26 | 2027-10-15 16:00 | Caracas FC vs San Lorenzo |
| SULA-PO-02:L1 | PO | 1 | 2027-08-26 | 2027-10-15 16:00 | Platense vs Emelec |
| SULA-PO-05:L1 | PO | 1 | 2027-08-26 | 2027-10-15 16:00 | Rosario Central vs Libertad |
| SULA-PO-06:L1 | PO | 1 | 2027-08-26 | 2027-10-15 16:00 | Universitario vs Universidad Católica |
| LIB-R16-03:L2 | R16 | 2 | 2027-09-07 | 2027-10-18 16:00 | Vélez Sarsfield vs O'Higgins |
| LIB-R16-07:L2 | R16 | 2 | 2027-09-07 | 2027-10-18 16:00 | Liverpool (URU) vs The Strongest |
| LIB-R16-08:L2 | R16 | 2 | 2027-09-07 | 2027-10-18 16:00 | Sportivo Luqueño vs Atlético Nacional |
| SULA-PO-01:L2 | PO | 2 | 2027-09-02 | 2027-10-18 16:00 | San Lorenzo vs Caracas FC |
| SULA-PO-02:L2 | PO | 2 | 2027-09-02 | 2027-10-18 16:00 | Emelec vs Platense |
| SULA-PO-05:L2 | PO | 2 | 2027-09-02 | 2027-10-18 16:00 | Libertad vs Rosario Central |
| SULA-PO-06:L2 | PO | 2 | 2027-09-02 | 2027-10-18 16:00 | Universidad Católica vs Universitario |
| reserve:LIB:QF:L1 | QF | 1 | not assigned | 2027-10-21 16:00 | Reserved, up to 16 possible qualifiers |
| reserve:SULA:R16:L1 | R16 | 1 | not assigned | 2027-10-21 16:00 | Reserved, up to 24 possible qualifiers |
| reserve:SULA:R16:L2 | R16 | 2 | not assigned | 2027-10-28 16:00 | Reserved, up to 24 possible qualifiers |
| CDB:QF-03:L2 | Quartas | 2 | 2027-09-22 | 2027-11-10 18:00 | Botafogo vs Flamengo |
| CDB:QF-01:L1 | Quartas | 1 | 2027-09-15 | 2027-11-10 20:00 | Fluminense vs Cruzeiro |
| CDB:QF-04:L1 | Quartas | 1 | 2027-09-15 | 2027-11-10 20:00 | Athletico-PR vs Bahia |
| CDB:QF-02:L1 | Quartas | 1 | 2027-09-15 | 2027-11-11 16:00 | Fortaleza vs Palmeiras |
| CDB:QF-04:L2 | Quartas | 2 | 2027-09-22 | 2027-11-24 18:00 | Bahia vs Athletico-PR |
| CDB:QF-02:L2 | Quartas | 2 | 2027-09-22 | 2027-11-24 20:00 | Palmeiras vs Fortaleza |
| CDB:QF-01:L2 | Quartas | 2 | 2027-09-22 | 2027-11-25 16:00 | Cruzeiro vs Fluminense |
| CDB:SF-01:L1 | Semifinais | 1 | 2027-10-13 | 2027-12-02 16:00 | Reserved, up to 4 possible qualifiers |
| CDB:SF-02:L1 | Semifinais | 1 | 2027-10-13 | 2027-12-02 16:00 | Reserved, up to 4 possible qualifiers |
| reserve:LIB:QF:L2 | QF | 2 | not assigned | 2027-12-05 16:00 | Reserved, up to 16 possible qualifiers |
| reserve:SULA:QF:L1 | QF | 1 | not assigned | 2027-12-05 16:00 | Reserved, up to 24 possible qualifiers |
| CDB:SF-02:L2 | Semifinais | 2 | 2027-10-20 | 2027-12-08 16:00 | Reserved, up to 4 possible qualifiers |
| CDB:SF-01:L2 | Semifinais | 2 | 2027-10-20 | 2027-12-08 18:00 | Reserved, up to 4 possible qualifiers |
| reserve:SULA:QF:L2 | QF | 2 | not assigned | 2027-12-15 20:00 | Reserved, up to 24 possible qualifiers |
| reserve:LIB:SF:L1 | SF | 1 | not assigned | 2027-12-22 21:00 | Reserved, up to 16 possible qualifiers |
| reserve:SULA:SF:L1 | SF | 1 | not assigned | 2027-12-22 21:00 | Reserved, up to 24 possible qualifiers |
| reserve:LIB:SF:L2 | SF | 2 | not assigned | 2027-12-25 21:00 | Reserved, up to 16 possible qualifiers |
| reserve:SULA:SF:L2 | SF | 2 | not assigned | 2027-12-25 21:00 | Reserved, up to 24 possible qualifiers |
| reserve:LIB:FINAL:L1 | FINAL | 1 | not assigned | 2027-12-28 21:00 | Reserved, up to 16 possible qualifiers |
| reserve:SULA:FINAL:L1 | FINAL | 1 | not assigned | 2027-12-28 21:00 | Reserved, up to 24 possible qualifiers |
| CDB:FINAL-01:L1 | Final única | 1 | 2027-12-05 | 2027-12-31 21:00 | Reserved, up to 8 possible qualifiers |

Unresolved constraints and commissioner decisions:

- 12 inherited league turnarounds below 72 hours remain unchanged (minimum 68h)
- 72h is kickoff-to-kickoff including travel, not 72h recovery plus travel; six extra travel hours proved infeasible in this conservative model
- Foreign domestic schedules, distances, venues and travel itineraries are absent; no global-calendar guarantee
- December 25 semifinals and December 28/31 finals require commissioner acceptance of a year-end extension within 2027
- Long inter-leg gaps are a consequence of preserved league fixtures and worst-case multi-competition capacity
- Downstream continental pairings/venues are undrawn; reservations block every possible contender and must be refined once draws exist

The 72h interval includes travel. Travel is considered by marking international events, conservative qualifier pools and the rejected extra-buffer scenario; actual itineraries are unknown. It is not 72h of recovery after travel.

## Finance before / after (BRL)

| Measure | Save 046 | Candidate 046C |
|---|---:|---:|
| Restricted cash | 31,930,000.00 | 30,550,000.00 |
| August missing incremental cash debit | 1,380,000.00 unbooked | 1,380,000.00 paid once on Sep 26 |
| September accrued unpaid incremental wages | Not separately recorded | 1,559,000.01 |
| September full-month obligation under proposed proration | Not separately recorded | 1,799,666.67 |
| Cash less recorded September liability | Not reconciled | 28,990,999.99 |
| Acquisition authority remaining | 1,400,000.00 | 1,400,000.00 |
| Annual incremental wage commitments | 21,660,000.00 | 21,660,000.00 |
| Annual wage headroom | 340,000.00 | 340,000.00 |
| Scouting / agent headroom | 2,190,000.00 | 2,190,000.00 |
| Restricted emergency reserve | 16,000,000.00 | 16,000,000.00 |

August covers the January three signing contracts (R$310k + R$430k + R$640k). September additionally includes Arthur Dias from Sep1 and Barreal from Sep2. Actual calendar days, inclusive start dates, half-up rounding per obligation, month-end payment. January-July historical cash entries remain untouched.
No September cash debit, invented base-roster salary, new capital or duplicated annual-commitment expense is recognized. These are candidate bookkeeping policies, not recovered facts about an unspecified historical accounting convention.

## Administrative changes

Cup objectives: Carioca achieved, CDB achieved, Sudamericana failed; league, youth and Finance remain pending. Finance wording reflects R$68m authority. Structured progress corrects selected stale meta notes.
Changed tables: admin_operations, admin_policies, board_objectives, calendar_events, cdb_2027_bracket, cdb_2027_plan_meta, checkpoint_info, finance_ledger, libertadores_2027_meta, libertadores_2027_round_of_16, meta, payroll_obligations, payroll_periods, schema_migrations, sudamericana_2027_playoffs.
`operations.json` and `admin_operations` enumerate 119 changed/inserted keyed rows, with complete before/after images and reasons. `changes.json` also includes every log row itself (238 total keyed row changes). Schema DDL is recorded by migration ID/hash. Log rows are validated by independent replay, without recursive self-logging.

## Validation findings

- PASS [046c.parent]: Parent independently passes frozen Save 046 checks and SHA256
- PASS [sqlite.integrity]: ['ok']
- PASS [sqlite.foreign_keys]: Declared foreign keys remain valid
- PASS [046c.calendar_model]: Stage order, fixed league dates, potential qualifiers, rest and workload validated
- PASS [046c.schema]: Exact authorized migration schema; no unexpected objects
- PASS [046c.table_inventory]: Original tables retained; seven explicit administrative tables added
- PASS [046c.historical_records]: All 56 protected tables including every fixture, event, player and transfer unchanged; drift: []
- PASS [046c.authorized_delta]: Every table equals independently replayed authorized migration; unexpected: []
- PASS [046c.provenance]: Version, parent, schema, plan hash and candidate status retained
- PASS [046c.finance]: Cash R$30,550,000; accrued unpaid September incremental wages R$1,559,000.01
- PASS [046c.payroll_unique]: Nine unique periods, eight unique cash postings; no September cash debit
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
- WARN [046c.calendar_exceptions]: 12 inherited fixed league turnarounds under 72h retained; added cup/rest reservations comply
- WARN [046c.commissioner_calendar]: 72h includes travel; extra 6h model infeasible; Christmas semifinals, Dec28/31 finals, long inter-leg gaps and foreign calendars require review
- WARN [046c.commissioner_finance]: Actual-day/month-end payroll policy is proposed; untracked base salaries excluded; no canonical promotion

## Phase 2 readiness

Checkpoint infrastructure is ready for engineering review. Resolve/accept calendar and accounting policy choices before canonical promotion or any official match simulation. No R26 execution is authorized by this artifact.
