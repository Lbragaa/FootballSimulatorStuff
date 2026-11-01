# Season authorization boundary — PR #11 development

This implementation connects season review to the **existing** lineage signer,
registry, accepted parent, fencing and parent claims. It does not register a
production multiseason continuation profile. Production keys, worker, accepted
career, automatic mode, private GitHub ledger and checkpoints are untouched.
PR #11 remains dependent on PR #10.

## Working scope

`braga_era.season_authority.prepare` authenticates the actual current accepted
parent through `lineage.parent_info`. A closed proposed policy binds recorded
2027 closure, 2028 migration and its exact DDL hash, engine/model policies, offseason policy, exact
database and checkpoint hashes, authority epoch, next generation and the
**existing** career seed hash. No seed argument exists. All covered tournaments
must be complete, administrative obligations settled and stored narration fully
revealed. The closure verifier rejects unscoped competitions and incomplete
commitments, rather than taking an empty agenda as sufficient evidence.

`authorize` requires a separately signed exact manifest/policy decision. The
existing registry transaction stores the proof and `season_authorized` batch,
claims its parent, and appends the existing decision log. Ordinary delegated
gameplay cannot produce this action. Competing transitions/batches cannot acquire
the same parent. Crashes before commit roll back; crashes after commit resume
the same receipt. Neither approval nor rehearsal changes the accepted head.

`rehearse` is explicitly restricted to TEST authorities and the original local
candidate destination. It authenticates the signed policy and parent claim,
retains the lineage seed, uses the existing additive multiseason migration and
commits a deterministic child UUID for `prepare_season(2028)`. Exact retries
replay the existing operation. Independent full replay and the existing portable
export/restoration verifier remain mandatory. Unexpected operations, modified
parents/policies, fenced authorities and replacement destinations fail closed.

No new authority schema or signing-key provisioning is needed. Existing
`batches`, `parent_claims` and `decisions` hold the review proof. No new snapshot
is created by preparation/approval/status. The DEV rehearsal retains its existing
parent/database copies only inside disposable tests. The old production executor
rejects `season_authorized` as an execution state; the DEV candidate cannot be
passed off as an accepted production successor.

`season_status` exposes a read-only signed bridge projection. Empty ordinary
episode/automatic agendas now stop at an explicit season boundary. No full-time
score, winner or final table is exposed before every stored match is revealed.
Only after authenticated closure does it include final standings, recorded world
trophies and the existing incremental financial statement, with its scope limits.
Existing cached
responses, narration pages, UUIDs and protocol-2 sequences remain unchanged.

## Evidence and limits

Baseline `ebe2cf2` passed all six Windows/Linux Python 3.11–3.13 jobs in
[run 87](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/41216847527),
including Linux 3.12's complete original/offseason 2028 and 2029 rehearsals.
PR #10's open active-round continuation finding is fixed in PR #11 and remains
covered by the existing episode regression tests; the dependency is not merged.

New tests create a completed, accepted 2027 **TEST** checkpoint through the real
lineage prepare/authorize/execute/verify/accept APIs. Fixture setup starts at the
post-delivery boundary using sealed exact final cursors; it does **not** claim
to demonstrate phone narration of every 2027 match. Tests then cover exact
approval, interrupted transactions, claim fencing, seed/policy rejection,
unrevealed narration, corrupted parents, TEST migration and independent restore,
and a protocol-2 worker command/reply retry with no controls enabled.

Local verification passed: eight authority integration tests in 934.04s, one
additional exact-schema policy check, 41 episode/protocol/automatic regressions
and 29 lifecycle/worker regressions. These sets contain 79 passing tests. Local
execution used Python 3.14.3 with existing pytest 9.1.1 libraries because the
development venv's external Python 3.12 base could not import `enum`; neither
that base installation nor the production runtime was modified. Windows/Linux
Python 3.11–3.13 verification runs through the existing CI matrix; new-head CI
is not claimed green while it is still running.

The first integration attempt correctly failed because the fixture assumed
`world_cursors` existed for undelivered matches. Post-delivery fixture setup now
uses each actual `world_receipts` result hash and its final recorded event
sequence. The closure/reveal guard was not weakened, and both attempts used the
same precommitted TEST career seed. The successful run verifies all 217 forward
TEST fixtures through the existing lineage path before the transition tests.
This 934s includes that parent construction and repeated independent replay;
it is a test lifecycle duration, not an episode/rolling-performance benchmark.

Both runs' raw test databases were disposable and cleaned up. The established
compressed development archives were neither extracted nor changed. No new
rehearsal databases are kept in visualizations, `.tmp` or the live career tree.

This is the first coherent authority/bridge boundary, not the full requested
2028-through-2029 authority rehearsal. Successor registration, exact-hash season
acceptance, recurring season profiles, season-aware match navigation/narration,
offseason phone episodes and rolling attestations are still unfinished. There
is no new whole-season or rolling-performance claim. Previous verified 1,341/
312/2029 artifacts remain immutable in compressed local development archives.
No full rehearsal databases are retained or uploaded to GitHub.

Two concrete incompatibilities prevent simply accepting the DEV directory with
the old production profile: the existing archive format has a 256,000,000-byte
expanded bound, while the verified offseason 2028 database alone is 303,788,032
bytes; and current gameplay navigation/standings still use 2027 world fixtures
and league membership. Both need a new reviewed profile and edition-aware
integration, not relaxed validation or a larger unversioned size limit. The
existing `results.Projection` already reads multiseason fixtures/editions and
should be reused for season-aware reporting.

## Remaining activation work and decisions

1. Register and independently audit a season-capable continuation profile and
   exact successor acceptance over the immediate parent, including backup,
   restoration, authority transfer, automatic revocation and narration fencing.
2. Connect that profile to edition-aware gameplay/history and signed offseason
   episodes, then run the full 2028/2029 rehearsal through that actual path.
3. Implement rolling verified parent commitments and bounded storage; benchmark
   multiple successors with wall/CPU/memory/export/restore/acceptance costs.
   Existing DEV incremental sealing and duplication limitations still apply.
4. Commissioner review: missing 2027 Série B/state/foreign qualification inputs
   need explicit administrative evidence decisions; no historical scores may be
   fabricated. Non-RJ federation/CDB coverage still needs completion.
5. Commissioner review: hypothetical liquidity/revenue, modeled ages, youth,
   retirement and transfer economics require calibration and approval. Guaranteed
   contract release compensation and richer market timing remain incomplete.
6. After all gates and rehearsals pass, obtain separate production migration,
   policy and exact transition authorization/acceptance. No such authorization
   is inferred here from standing 2027 gameplay delegation.

Material policy choices remain unapproved:

| Decision | Alternatives and consequences | Recommendation for review |
| --- | --- | --- |
| Missing 2027 access evidence | Documented administrative berths; or prospective ACCESS competition. Neither supplies historical Série B scores. | Choose an explicit one-time transition input, then use recorded division results thereafter. |
| Non-RJ cup qualification | Extend state competition coverage; or evidenced federation allocation with explicit gaps. | Bound the required federations and source each entrant; block unsupported entry routes. |
| Club economics | Recorded accounts only (unknown clubs cannot spend); or separately approved modeled opening finances/revenue. | Calibrate club-specific forward scenarios and liabilities; preserve Vasco reserve and authority restrictions. |
| Unknown ages/youth | Freeze uncertain development; or approve explicit modeled age and academy policies. | Review longitudinal population and quality distributions before approving the model. |
| Guaranteed releases | Continue refusing them; or approve a compensation/liability mechanism. | Keep refusal until compensation is implemented, funded and tested. |
| Market timing | Existing bounded January clearing; or daily windows with negotiations and competing offers over time. | Complete and calibrate the richer window before describing it as a full transfer market. |

None of these recommendations is a commissioner decision or execution authority.
