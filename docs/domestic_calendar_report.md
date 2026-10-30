# Shared domestic and continental development season

Implemented on PR #11, still dependent on PR #10. This is disconnected,
nonpromotable development evidence. No production registry, accepted career,
worker, signing key or official match was accessed or changed.

## Working formats and measured integration

One persistent world completed these 2028 competitions chronologically using the
existing match engine, player overlay, deterministic commitments and signed
operation store. There were **1,341 real simulated matches / 527 operations**,
followed by full independent replay, export and independent restoration.

| Edition | Format / completed matches |
| --- | --- |
| Série A | 20 clubs, double round robin: 380 |
| Série B | 20 clubs, double round robin: 380 |
| LOWER | Proposed eight-club forward lower pathway: 56 |
| ACCESS | Initial prospective qualification, not historical Série B: 8 |
| Copa do Brasil | 128 entrants, nine stages: 157 |
| Carioca | Two groups of six, cross-group league, QF/SF/final: 45 |
| Supercopa | Recorded prior league/cup champions, one final: 1 |
| Recopa | Recorded prior continental champions, two legs: 2 |
| Libertadores preliminaries | PRE1 6, PRE2 16, PRE3 8 |
| Sudamericana national preliminary | 16 |
| Libertadores main stages | Groups and complete knockouts: 125 |
| Sudamericana main stages | Groups, cross-entry playoffs and knockouts: 141 |

All editions closed, their decisions were archived, and all three national league
tables reconcile directly to scores. Every club met the committed 72-hour rest
policy; venues and blackout intervals were checked. Full rehearsal wall time was
617.487 seconds, including its verification/package work. This is a single new
workload measurement, not a before/after episode benchmark.

A separate bounded SP state-qualifier test played all seven games of an
eight-club knockout and checked next-year sporting evidence. It was **not** part
of the 1,341-match combined calendar and is not a full Paulista implementation.

The 2029 continuation retained the same 48 national club identities. The actual
top/bottom finishes move four clubs between A/B and B/LOWER, with no new arbitrary
admissions. Two national matchdays produced **48 matches** (20 A, 20 B, eight
LOWER). Original 2028 scores, receipts and source package bytes were unchanged;
549 operations independently replayed and restored. Wall time: 715.739 seconds,
dominated by repeated full-history verification. This proves national transition
repeatability, not a complete 2029 ecosystem.

[Counts, hashes and reconciliation](validation/shared_domestic_2028.json) omit
scores and private credentials. All evidence concerns test outcomes only.

## Explicit proposed policies

`domestic-ecosystem-development-1` implements CDB entry counts 36/66/6/20 at
stages 1/2/3/5; stage participant counts are 36, 84, 48, 24, 32, 16, 8, 4, 2.
Stages 1–4 and the final are single matches; stages 5–8 have two legs. Tied
decisive results go directly to penalties; the final is neutral. Every draw and
participant source is recorded. Late entry requires actual current Série A
membership. Sporting early-entry evidence must identify the recorded prior state
finish or a supported regional/access champion. Duplicated clubs are rejected.

This is a proposed 128-entry adaptation informed by the
[CBF regulation](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/REC_Copa_do_Brasil_2026_66989a5426.pdf),
which announces expansion from 126 to 128 clubs from 2027. The first two stage
sizes are an explicit mathematical adaptation, not an authenticated 2028 rule.
Full federation quotas, replacement and national ranking selection remain missing.

Carioca commits two strength-balanced groups in entries **and** the signed
creation receipt. All 36 cross-group fixtures must match those pools. Top four
per group enter single QFs, two-leg SFs and a neutral single final: 45 matches.
Ties use direct penalties. The
[FERJ format announcement](https://fferj.com.br/noticias/carioca-2026--clubes-aprovam-regulamento)
informs the 12-club/two-group/ten-date proposal; this game's exact forward rules
still require review. Clubs cannot enter two state federations in one season.

Supercopa uses the recorded league runner-up if the same club won both domestic
titles. A same-club Recopa source fails closed; no opponent is manufactured.
`divisions-development-1` retains initial 2028 missing-B admissions as named
administrative scenarios; from 2029 it uses actual recorded standings exclusively.
`follow-national-division-bans-1` explicitly carries unserved bans into the new
division while preserving original counters.

## Shared calendar and state

`shared-season-calendar-development-1` commits edition/stage/leg date slots,
closed international intervals and venue bindings before fixtures. Conditional
stages activate only after their recorded prerequisites. No unknown winner is
assigned to a reservation. Every scheduling operation checks shared clubs,
72-hour rest, venues, holidays and global kickoff/completion boundaries. An
unsatisfiable reservation rolls back with the actual conflicting fixture context;
constraints never silently relax. Agenda request IDs include edition and action.

The tested international windows and individual-ground bindings are explicitly
fictional assumptions, not verified FIFA dates or real stadium/travel data.
Travel is included in the established 72-hour model, not separately simulated.
The calendar cache lives only inside one connection-bound scheduling transaction;
independent replay rereads the committed inputs.

Player fitness, medical status, discipline and registration use the existing
shared overlay across competitions. A new opt-in country-group opcode derives
Brazilian nationality from actual recorded league membership. Frozen legacy
country-draw operations retain their previous strict behavior and hashes.

## Economics, offseason and remaining acceptance blockers

Existing annual evolution and modeled-registration continuation were exercised;
this milestone does **not** add a complete autonomous transfer market. Contract
expiry/free agents, competitive offers, agent fees/installments, youth/retirement,
foreign club planning and sustainable all-club budgets remain unfinished.

The run uses an explicitly hypothetical R$3 million/month incremental income
scenario for known Vasco contracts. Twelve payroll periods settle exactly once,
cash postings reconcile and the reserve is preserved. Unknown base payroll and
other club finances are **unknown**, not silently funded or zero-valued. The
read-only audit checks archived year-end accounts independently of later seasons.
No scenario income is approved canonical revenue or owner capital.

Full non-RJ state calendars, all-federation CDB qualification/deduplication,
complete offseason/economics, a complete 2029 repetition, and season-aware
production authority/bridge/narration remain acceptance blockers. Foreign entry
orders and initial missing domestic sources remain labeled development scenarios.
The source was an authenticated completed **NONCANONICAL** 2027 fixture, not a
read of the current official career. **THE BRAGA ERA is not yet 2028-ready.**

## Reproduction and tests

Run only against a completed NONCANONICAL 2027 fixture and new output directories:

```sh
python -m tools.rehearse_domestic_season --db output/ci-season/database.sqlite --output output/shared-2028 --continental
python -m tools.rehearse_domestic_transition --package output/shared-2028/portable --output output/shared-2029
```

New regressions cover domestic inventories, state identity conflicts, recorded
supercup eligibility, immutable Carioca pools, complete tournament execution,
venue/rest failure rollback, blackout rejection and connection-local cache scope.
The CI matrix retains Windows/Linux Python 3.11–3.13. Its Ubuntu 3.12 job also
runs the combined season, 2029 continuation and incremental benchmark. Only safe
test JSON evidence is uploaded by the new steps; no keys or databases.

Baseline `05a6861` passed all six jobs in
[run 75](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/41108359761).
That success does not certify subsequent changes; new-head CI must be checked.
