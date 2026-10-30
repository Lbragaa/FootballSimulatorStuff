# Implemented multi-season development execution

Latest: [266-fixture continental main-stage proof](continental_main_stage_report.md)
adds SULA cross-playoffs, group-winner byes, R16 home orientation and independently
restored full-sized group/knockout paths. Allocations/preliminaries/country draws
are still missing; the older limitations below describe their respective stages.

Continuation: [working group-stage and query optimization evidence](group_stage_continuation.md)
adds a real-engine 24-group-match + five-knockout-match test through a champion,
recorded LIB third-place cross-entry evidence, and 17.9% lower wall time for an
identical team-loading workload. The prior 285-operation/417-fixture rehearsal
still replays to the same hash. These additions do not complete continental
preliminaries, allocations, SULA playoffs or the full ecosystem described below.

This extends PR #11 beyond planning. It is **not 2028-ready** and is not installed
in the production worker. No official match, acceptance, migration, key change,
registry change or fictional-clock advance was performed.

## Working implementation

`braga_era.multiseason` is the separate `DEV-MULTISEASON-2` profile. It reuses the
existing regulation engine, autonomous coaches, forward configuration, ET and
penalty resolver/validator, shared elapsed-time fitness and player updates.
There is no second match engine or new transport.

The explicit additive migration creates edition/entry/qualification/fixture/tie
records; season archives; signed operations and bounded run journals; contracts,
loans, accounts, ledger and payroll records; effective annual attributes; and
explicit proposed-income schedules. Edition identities include the season.
Existing 2026/2027 tables are retained. Native history is immutable; old world
club rows are immutable with additive fictional clubs allowed. Current player
overlays evolve while original snapshots/appearances and native identities stay
unchanged. Archived Savarino #196 is not made eligible.

TEST-only migration decisions bind exact parent bytes/checkpoint, DDL, policy and
seed. The first migration refuses an unfinished 2027. Closed commands use signed,
hash-chained receipts, SQLite transactions, canonical request UUIDs and exact
retries. Simultaneous groups persist snapshots/config/seeds **before** draws;
all inputs share one pre-kickoff state. Engine validation precedes atomic result
application. Claimed groups fence unrelated world mutations and cannot be
exported as completed checkpoints. Crashes preserve claims and original seeds.

Independent verification checks exact schema inventory, preserved source tables,
operation signatures and a complete fresh reconstruction from the immutable
migration parent. Portable directory export verifies the copied artifact before
publication; restoration repeats full reconstruction. Packages refuse unexpected
files, symlinks, oversized metadata and total size above 2 GiB. This profile
still replays all operations since migration; immediate-parent incremental
production lineage is **not implemented** for it.

Implemented competition mechanisms:

* Complete 20-club double round robin, standings and deterministic champion.
  Prototype ranking is points, wins, goal difference, goals scored, then stable
  club key. That last fallback differs from the inherited name fallback and is
  not an approved official 2028 rule; keep the versioned rehearsal reproducible
  and resolve the official forward ranking before activation.
* Evidence-backed 16 survivors plus four recorded promoted clubs for Série A;
  arbitrary proposed pools cannot supply Série A places.
* Prospective eight-club/four-tie access qualification, two legs and recorded
  aggregate/penalty winners. It invents no historical Série B table/results.
* Generic two-leg/single-final knockout stages, committed seeded draws over
  actual qualifiers, subsequent-stage dependencies, orientation, ET/penalties
  and champions. Registry IDs include CDB, Carioca, other state, LIB, SULA,
  Supercopa and Recopa, but **a registry ID is not a completed tournament adapter
  or complete entry policy**. Continental groups/cross-entry remain missing.
* Shared 72-hour club rest/holiday scheduling with conservative separation of
  distinct kickoff groups. Conflicts fail closed. No automatic calendar skipping.

Implemented market/evolution mechanisms:

* Recorded cash/reserve/budget accounts; purchases/sales with balanced fee
  postings, positive wages, effective contracts, transfers and ownership changes.
* Loans, no conflicting active loans, expiry returns and actual-day wage sharing.
* Renewals, unique active contracts, month-end payroll and duplicate prevention.
* Autonomous positional/affordability/negotiation prototype with stable streams;
  Luan remains Vasco's autonomous coach. Clubs with unknown opening finances
  receive no invented spending money or wage authority.
* Bounded annual ability changes from recorded career phase/potential and stable
  per-player streams. Unknown ages remain unknown, not fabricated birth dates.
* Explicit modeled-registration continuation and optional versioned carry of
  unserved suspensions (with yellow reset). These are proposed policies. The
  integrated rehearsal below predates the optional carry command; sanction
  carry is independently tested and is a remaining integration gate.

`results.Projection` now also projects edition fixtures, aggregates, penalties
and qualifiers. Historical reads still write nothing and withhold unrevealed
Vasco scores. `multiseason.views` derives player season statistics and coach
records from stored performances/committed manager choices. Normal production
bridge commands and signed cursors are unchanged; this development profile
cannot be attached to them yet.

## Verified disconnected rehearsal

`tools/rehearse_multiseason.py` authenticates the **actual current accepted
parent**, copies it into disconnected worlds and finishes 2027 twice with the
original committed career seed. It checks both completions are identical and
protects every already accepted result through `lineage.prefix_check`. It never
copies the signing key, touches bridge sequences or provisions production
authority. New migration/operation signatures use a public simulated TEST key.

The completed rehearsal generated eight explicitly fictional Brazilian access
clubs (strength priors 65–72), played their eight qualification legs, admitted
the four recorded winners plus the sixteen actual 2027 survivors, and played:

| Development edition | Completed fixtures | Result |
| --- | ---: | --- |
| Prospective ACCESS | 8 | Four qualifying winners; intentionally no champion |
| Brasileirão 2028 | 380 | Complete table and champion recorded |
| CDB 2028 scoped R16-entry prototype | 29 | All declared legs/final and champion recorded |

2027 and this **limited** 2028 scope were archived; 2029 was prepared through the
same lifecycle. All **417 fixtures / 285 signed operations** independently
replayed and restored, including a fresh-process restoration against current
code. Player goal totals reconcile with recorded match goals; coach participation
totals reconcile with all fixtures (476 appearing players, 24 club/coach records).
No scores or future Vasco outcomes are in the public engineering evidence.

The rehearsal explicitly supplied a **hypothetical R$3,000,000/month income
scenario** for known incremental expenses. It is not a real sponsorship, a
canonical income policy, full club accounts or implicit owner capital. Both the
eight new access clubs and this economic scenario need commissioner review;
their successful simulation is not approval. Unknown base payroll and other
clubs' economics remain unresolved. Cash postings reconcile, reserve remains
protected and twelve payroll periods settle once. Portable package size was
207,641,680 bytes. [Safe rehearsal evidence](validation/multiseason_rehearsal.json)
contains counts/hashes and limitations, not match results or secrets.

## Performance and testing

The reusable canonical-encoder configuration preserves exact JSON bytes and all
seeds/signatures. It caches no data or validation. Paired serialization benchmark
was 1.50×; the identical 16-match verified pipeline improved from 204.688s to
190.278s (7.04%) with the same semantic hash and full independent restoration.
See [comparison](validation/encoding_optimization.json). Single instrumented
runs do not establish a general episode speedup. New-profile parent checks use
the authenticated whole-file hash, rejecting parent WAL/journal sidecars;
complete logical history/schema/replay checks still run at verification/export.

Local tests: **406 core/compatibility checks passed**; all **17 new profile tests
passed together in 330.54 seconds**, followed by current-code recovery/history checks.
Coverage includes signed migration rejection, missing qualification, source
preservation, simultaneous inputs, replay, exact retries, concurrent requests,
crash before/after commit, claimed-world fencing, knockout finals, purchases,
loans/returns, pro-rata and duplicate payroll, reserve/budget failure, annual
development, sanction carry, read-only new-season history, proposed-income
accounting, archive/2029 preparation, and portable tamper rejection. The
Windows/Linux Python 3.11–3.13 CI now prepares/validates its existing full-2027
fixture before tests so these cases run rather than being skipped.

## Exact boundaries before production

The migration and competition/market prototypes work; the complete requested
football universe does **not** yet pass an integrated rehearsal. Remaining work:

1. Complete CDB early entry, continental preliminaries/groups and SULA/LIB
   cross-entry, country allocations, full state scope, Supercopa/Recopa and
   a full recorded Série B season. The 417-match run proves none of these missing
   paths by substitution with a knockout-only template.
2. All-club economics, agent fees/bonuses/installments/amortization, richer
   competing offers/free agents, complete contract expiry handling, youth and
   retirement. Current phase-based development is not full age calibration.
3. Integrate sanction/registration policies, all competitions and autonomous
   offseason decisions in a complete 2028 rehearsal, then play 2029 too.
4. Registered production transition authority, immediate-parent delta profile,
   approval/promotion, season-aware signed narration, full phone bridge commands
   and complete-season rehearsal. Current phone play remains on its installed
   profile and never silently activates 2028.

Material commissioner decisions: real fictional lower-division/access pool and
promotion route; future competition formats/allocations/state scope; explicit
economic assumptions/budget authority; unknown-age/registration/sanction priors.
The test assumptions are review candidates, not a request to approve software
as gameplay authority. No deployment or merge is authorized by this report.
