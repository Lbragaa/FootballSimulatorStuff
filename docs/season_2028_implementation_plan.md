# Multi-season implementation plan

Status: Stage A and the first isolated Stage B foundation. **Not ready to run
2028.** No production migration, activation, worker installation, match execution
or acceptance is part of this change. Policies below are proposals, not approvals.

## Current contracts and evidence

Discovery on 2026-10-29 authenticated the current registered production parent
through `Career.identity` and `lineage.parent_info`, rather than assuming root
046C. Its database has 90 user tables. The read preserved registry and key hashes.
No raw production database, unpublished result or signing material is included in
this document. Private status #1 remains the live head/sequence source; the career
can continue independently while this branch is developed.

The top sections of AGENTS.md, `docs/play.md`, `bridge_protocol_v2.md`,
`historical_results.md`, `bridge/automatic.py`, `bridge/episode.py` and the actual
lineage implementation govern current play. The roadmap's Task 03B status and
the initial paragraphs of the Task 03D runbook predate authorized gameplay.
Their root-only dates and manual-only descriptions describe historical stages,
not the live head. Keep their frozen evidence; do not apply obsolete dates to
the current career. Earlier engine/profile versions remain replay contracts.

| Domain | Existing implementation | Multi-season limitation / boundary |
| --- | --- | --- |
| History | Native fixtures/events/shots/player_matches, cup_ties, competition_history, league_standings_archive, world_finals; `results.Projection` deduplicates mirrors | Heterogeneous schemas and incomplete early archives; dates do not always identify season |
| Prospective world | `world_fixtures` already has season; adapters preserve native mirrors and stable global IDs | Adapters, progression and much SQL explicitly refer to 2027; league IDs currently use native integer IDs |
| Competition decisions | world_ties, world_draws and world_champions | Ties/draws lack explicit season columns; champion PK is competition alone; copying these unchanged would mix seasons |
| Calendar | Shared kickoff/completion agenda; simultaneous snapshots; conditional draw reservations; month ends | Initial reservations and obligations are 2027-specific; no next-year generator |
| Football | Immutable snapshots/config, named RNG streams, autonomous coaches, regulation and ET/shootout validation | Retain the existing engine; introduce season adapters, not a second match engine |
| Players | Stable native IDs + persistent explicitly fictional world_players; shared medical/fitness/form state, competition bans | No longitudinal attribute history, youth/retirement workflow or general transfer ownership ledger; archived #196 and active #354 remain distinct |
| Contracts/market | transfers, transfer_contracts, market_negotiations_2027; contract eligibility in world.players | Legacy single-row player contract and narrative negotiations are insufficient for renewals, loans and competing offers |
| Finance | Integer-cent incremental payroll, period idempotency, cash ledger, annual budgets, reserve controls | Only recorded Vasco contracts are costed; no complete all-club accounts, future revenue or approved 2028 budget |
| Authority | Signed immediate-parent profile 2, career seed, fixture/parent/obligation claims, independent delta replay, immutable accepted proofs | Policy/model fixed by exact registered versions; inventory rejects boundaries after 2027-12-31 |
| Narration/bridge | Signed result-bound cursors/page IDs, stable UUID inbox/outbox, automatic delegation, ordered episode delivery, read-only historical pages | Episode/table SQL assumes 2027; standing gameplay does not authorize a new policy or migration |
| Packages | Exact manifests, root+immediate parent, logical fingerprints, reversible journal, independent restore/replay | Strict schema audit forbids unregistered additive tables/indexes; future migrations require a new profile |

All existing result hashes, receipts and seed commitments must continue verifying
under their original code/profile. No new schema is installed into those files.

## Competition inventory and proposed supported scope

Counts below describe recorded coverage, **not completed-season claims**. The
discovery projection found league 2027's 380 fixtures and five Carioca final-four
matches. CDB 2027 has legacy early legs plus forward knockout records. Continental
groups have 96 fixtures per tournament; native R16/playoff and forward later
rounds/reservations supplement them. Their completion changes as the user plays.
Historical 2026 retains only 71 league fixtures, five CDB legs and the two
continental finals. Thirty-nine early 2027 league fixtures lack dates.

| Competition | 2027 evidence | Proposed 2028 implementation and decision |
| --- | --- | --- |
| Série A | Full 20-club/380-fixture inventory; 17th–20th relegation; inherited points,wins,GD,GF,name ranking | 20 entrants from verified survival + separately evidenced promotions; 38 rounds/380 fixtures. Pure undated draft implemented; participant qualification and calendar NOT implemented |
| Série B | No reliable 2027 table/results/participants found; only a documentary 2026 promotion decision | Block automatic 2028 entrants. Recommend a versioned prospective access-qualification competition from an approved eligible club pool after the actual current fictional date, with roster/calendar validation and recorded outcomes; do not label it historical 2027 Série B. An exceptional administrative allocation is an alternative commissioner decision, not a sporting table. Never backfill imaginary 2027 results. Future seasons need a real recorded supported Série B season |
| CDB | Legacy early rounds + recorded fixed late bracket, forward semifinals/final | Versioned entry routes, federation allocations, all supported rounds, draws and final. Do not reuse 2027 participants or silently adopt a new real format |
| Carioca | Explicit fictional top-four assumption; two-leg semis + neutral single final; no full state league | Recommend retain this disclosed bounded scope initially, subject to approval. A full participant pool/format needs separate evidence and calendar review |
| Other state championships | No complete recorded state ecosystem | Initially explicit qualification evidence panels and reserved calendar windows; no fabricated historical pyramid. If results affect entry, either implement that approved scoped tournament or fail closed |
| Libertadores | Established 2027 groups/R16, committed future draws and single final | Country allocations + titleholder routes + deduplicated qualifier ownership, preliminaries/group/knockout format, seeding/pots, country restrictions and calendar need approved versioned inputs |
| Sul-Americana | Established groups/playoffs, LIB third-place interaction and later rounds | Same requirements, with explicit cross-competition transfers/entry exclusivity and ordered prerequisites |
| Recopa | Not a current executable competition | Conditional on verified LIB/SULA champions and approved format/calendar; handle same-club champions by explicit replacement policy, never invent opponent |
| Supercopa | No complete executable adapter/qualified entry set | Conditional on league/CDB champions; same-club overlap requires approved runner-up route; budget/prize assumptions separate |
| FIFA/international extras | No complete eligibility/calendar ecosystem | Unsupported until qualified pool, rules and scheduling policy exist; do not manufacture annual events |

Authoritative reference material was checked for design context, not imported as
fictional 2028 rules: [CBF 2026 calendar announcement](https://www.cbf.com.br/a-cbf/noticias/informes-cbf/a/cbf-anuncia-novo-calendario-do-futebol-profissional-masculino),
[CBF CDB technical documents](https://www.cbf.com.br/futebol-brasileiro/noticias/supercopa-do-brasil/masculino/cbf-divulga-tabela-basica-plano-geral-de-acoes-e-regulamento-especifico-da-copa-do-brasil-2026),
[CBF Série B technical documents](https://www.cbf.com.br/futebol-brasileiro/noticias/undefined/ceara-x-guarani/cbf-divulga-documentos-tecnicos-do-brasileirao-da-serie-b-de-2026),
[CONMEBOL Libertadores 2026 manual](https://cdn.conmebol.com/wp-content/uploads/2025/12/CL-2026-Manual-de-Clubes-ESP-Feb26.pdf)
and [Sudamericana manual](https://cdn.conmebol.com/wp-content/uploads/2025/12/CS-2026-Manual-de-Clubes-ESP-Feb26.pdf).
These establish useful source documents, **not evidence of fictional 2028
participants/results or approved 2028 regulations**. A commissioner policy must
record chosen differences and source editions; no live real squads are imported.

## Proposed data and lifecycle design

Use one inherited world and the same authority/engine. New future tables should
be additive and explicitly enumerated by a new reviewed migration/profile:

* `season_cycles`: season ID/label, next-season link, lifecycle state, policy hash,
  immediate accepted parent, boundary and migration version.
* `competition_editions`: stable competition ID + edition/season, format/rules
  hash, start/end dates and closure scope. Dates may cross year boundaries.
* `edition_entries` and `qualification_decisions`: unique club/edition entries,
  route and exact source standings/title/commissioner decision. Allocate once,
  deduplicate cup/titleholder overlaps and record reassignment rules explicitly.
* Edition-keyed ties, draws, champions and standings, with globally namespaced
  fixture keys. Existing `league:402` and legacy keys remain unchanged; new IDs
  include edition identity. A compatibility adapter reads old tables in place.
* Append-only archive manifests referencing immutable full season snapshots and
  exact table/result/stat/finance hashes. Materialize season-scoped totals only
  from recorded appearances; retain unknown historical metrics.
* Versioned player attribute observations, registrations, contracts and economic
  operations effective at fictional times. Never rewrite historical attributes.

Lifecycle target: in_progress → finalizing → archived → offseason_preparation →
transfer_window → preseason → next_season_ready → active. Each arrow has an
immutable request ID, parent/policy/input commitments, before/after validation,
atomic application and exact retry. A transition must not itself advance time.

Closure requires a declared inventory, all required fixtures/conditional
dependencies resolved, champions recorded where required, complete administrative
obligations and no unresolved execution commitments. Cross-year editions are
explicitly excluded from closure by approved policy and retained with their
pending identities; never cancelled to make a season look finished. A date
alone, an empty agenda or a single championship flag cannot establish closure.

Archive every available sporting/statistical/finance/medical/contract/coaching
fact by exact snapshot reference before resets. Reset ONLY edition-specific
counters: league table, edition appearances and discipline where that edition's
policy permits. Carry player IDs, injuries/recovery timestamps, contracts,
registrations/loans, balances/reserve restrictions, manager identity/objectives,
career totals and unrevealed narration. No magical recovery at January 1.

The next profile must bind an approved migration and full policy bundle, exact
accepted completed parent, unchanged career seed and collision-free future
commitments. An exact transition authorization is separate from software review
and from subsequent ordinary gameplay delegation. Validate independently, export,
restore/replay, then require separate exact-candidate acceptance. Existing profile
2 rejects new season data; do not relax it to fit a candidate.

## Implemented first milestone

`braga_era/seasons.py` implements a **DEV sidecar**, not that future production
migration. `AcceptedSource.root` authenticates exact released root bytes;
`AcceptedSource.career` authenticates the registered current parent through existing
lineage. Trusted Python callers use those adapters; constructing the dataclass
manually is not an external authentication mechanism.

`create_rehearsal` refuses overwrites and atomically publishes:

* `parent.sqlite`: unchanged byte copy of the authenticated snapshot, containing
  all currently recorded facts; no new tables or counters added to it.
* `rehearsal.json`: nonpromotable scope, parent checkpoint/hash, exact schema/table
  fingerprints and closed proposed policy.
* `season.sqlite`: only `season_cycles`, `season_transitions`, `season_archives`.

No production/test authority, signing key or bridge transport is provisioned.
The sidecar is local development workflow storage, not a new career engine or
an official save. Fingerprints/hash chains detect corruption; they are not a new
cryptographic authority. Existing save profiles cannot promote this directory.

Implemented transitions stop at offseason_preparation. Remaining states are
reserved and reject execution until their real generators/validators exist.
`next_season_ready` cannot be asserted by ticking empty workflow steps. Archive
records commit the entire parent snapshot and retained cross-year obligations;
missing awards/coaching history stay missing. Source bytes are checked on every
operation; the sidecar journal independently reconstructs the state. Transactions
serialize concurrent runners and recover exact requests before/after commit.

`double_round_robin` implements a pure versioned Berger draft: 20 distinct clubs
produce 38 rounds, 380 distinct ordered pairings and 19 home/19 away matches per
club. Its sorted input and edition-prefixed keys are deterministic. It supplies
**no dates, qualified clubs, approved calendar, or permission to play**. Scheduling
must solve rest/travel across every competition, blackout, conditional bracket,
venue conflict and international window before publishing a playable season.

## Transfer, finance and evolution policy proposal

Recommended accounting is integer cents, explicit double-entry or reconciled
operation balances, and separate cash, budget authority, future liabilities and
amortization. Do not create opening cash for poorly documented clubs. Unknown
budgets mean recruitment is blocked or limited to explicit zero-cost permitted
operations, not unlimited spending. Keep Vasco's actual cash and restricted
reserve authoritative; a new season does not replenish either.

Each proposed move commits player, seller/current registration, buyer, transfer
window, effective date, fee installments, wage/bonuses/agent fees, budget source,
medical/registration checks and stable negotiation stream. Accept all-club
ownership/registration atomically; only then book authorized obligations. Loan
parent, wage shares, end date, return and purchase option must be distinct facts.
Contract versions retain renewals/expiry, payroll consumes the active interval
exactly once, and old transfers never generate duplicate wages through a JOIN.

Autonomous clubs assess positional shortfalls, depth, age, ability/potential,
availability, tactical fit and affordable total cost. Record rival bids, rejection
and negotiation failure. Luan's recommendations use his recorded preferences
under the same constraints; no favorable recruitment seeds. Extraordinary
capital and revenue assumptions require explicit commissioner decisions.

Propose bounded age curves with persistent per-player development streams and
effective-dated deltas, moderated by potential, minutes, injuries, training and
uncertainty. Avoid a second annual draw on retry. Retirement is an explicit
registered state; youth use a separate collision-free namespace and fictional
provenance. Reserve and foreign squads also evolve, without regenerating their
identities. Reputation/chemistry/objectives should change gradually from recorded
facts. Numerical curves, economics and youth rates remain unapproved/not coded
in this milestone; calibration must precede official use.

## Ordered implementation and acceptance gates

| Milestone | Deliverable / dependencies | Testable exit criterion |
| --- | --- | --- |
| A (this branch) | Inventory, policy gaps, pipeline baseline; preserve current software | Authenticated read only; no production writes or spoiler publication |
| B1 (this branch) | DEV closure/lifecycle/archive reference, generic undated league draft | Missing data blocks closure; duplicate/concurrent/crashed transitions preserve source; 2028/29/30 drafts reconcile |
| B2 | Season-scoped schema/profile and migration; resolve promotion evidence first | Independent before/after replay; all old tables/results unchanged; new edition constraints/FKs validated; no activation |
| C1 | Qualified pools, domestic formats, continental allocations and calendar solver | No duplicate entry, phantom club, shared-venue conflict or new sub-72h club gap; inherited approved exceptions separately identified |
| C2 | Same-engine generic adapters, stage draws/progression and champions | Every approved competition completes on isolated fixtures; broken dependencies fail closed |
| D1 | Effective-dated ownership/contracts/windows and reconciled economic operations | Fees/liabilities/payroll/loans balance; duplicate/competing acceptance rejected; no reserve breach |
| D2 | Calibrated age/youth/retirement/club evolution and autonomous recruitment | Stable streams, bounded distributions, non-Vasco symmetry, no changed historical observations |
| E1 | Profile proven hotspots and optimize narrowly | Same seed/results/events/logical state; independent validation still runs; measured before/after including warm/cold runs |
| E2 | Season-aware bridge reads/episodes and exact transition authorization | Old protocol/pages/UUIDs unchanged; no score leaks; season end yields review/blocker rather than silent activation |
| E3 | 2027→2028→2029 disconnected rehearsal, failure injection and review | Complete seasons, audited economics, independent restore/replay, retry/concurrency/size limits; exact commissioner review candidate |

B2/C/D can develop independently behind interfaces, but no schedule participants
can be finalized before qualification policy and no financial state can be
activated before a complete approved opening ledger. Approval of scope/format
does not approve invented past Série B results. Foreign federation allocations,
same-club title overlaps, windows, TV/venue congestion, unrecorded domestic
calendars and package growth are material dependencies, not minor defaults.

Performance work E1 can start immediately after A; it need not wait for the
new competition ecosystem. PR #10 remains open, so this foundation PR stacks on
`codex/career-episodes` without merging or rewriting it. Its existing review
finding about retaining an unfinished rodada across all resumable episode exits
is an additional compatibility gate before season-aware bridge work; this
foundation does not claim to resolve that separate episode behavior.

No full 2028 simulation, official migration, claimed performance speedup or
production deployment is delivered by B1. The precise next implementation is B2,
with commissioner review of promotion source, supported tournament scope,
qualification/format bundle, revenue/budget model and transition authority.
