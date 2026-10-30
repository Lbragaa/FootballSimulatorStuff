# Continental main-stage execution

Implemented and tested `sula_cross_playoffs` under explicit proposed policy
`sula-cross-playoff-1`, without changing the engine or existing schema/profile.
The two seeded entry pools are disjoint. All group results are simulated.
Eight recorded LIB group thirds enter SULA with qualification provenance; they
face eight SULA runners-up over two legs. Eight SULA group winners bypass that
playoff, then face its winners in R16 and host the second leg. Subsequent rounds
use actual winners, two-legged aggregates/direct penalties and a neutral single
final with existing ET/penalty validation. Completed qualification and tie records
remain queryable; reporting identifies group matchdays, playoff legs and ties.

## Actual complete test counts

| Stage | LIB | SULA |
| --- | ---: | ---: |
| Eight four-club groups, six matchdays | 96 | 96 |
| Cross-competition knockout playoff | 0 | 16 |
| Round of 16 | 16 | 16 |
| Quarterfinals | 8 | 8 |
| Semifinals | 4 | 4 |
| Single final | 1 | 1 |
| Total actually simulated | **125** | **141** |

`tests/test_sula_pipeline.py` runs both editions together through the shared
calendar and player-state layer, asserts all 266 final fixtures, 40 SULA entry
and qualification records, eight transfers, winner byes and R16 home orientation.
It independently replays, exports and restores the package and compares the
semantic hash. The final run passed in 227.39 seconds. No scores were injected.
The existing group/historical compatibility selection also passed 21 tests.

This is a **main-stage** rehearsal on roster-backed proposed pools, not the full
requested continental workflow: country allocations, defending-title overlap,
preliminary entry and country-restricted group draws are not yet implemented.
It must not be described as fully implemented Libertadores/Sul-Americana.
The test does not approve those pools or hypothetical development cashflow.

The earlier 417-fixture domestic rehearsal remains separate evidence. This run
does not constitute a combined full 2028 world or a new 2029 rehearsal. Domestic
entry/state/Série B integration, autonomous offseason expansion and production
authority/bridge work remain unfinished. No additional performance improvement
is claimed in this continuation; no verification was removed. The highest next
priority is allocation/preliminary/country-constrained entry connected to these
now-tested main stages, followed by the combined calendar rehearsal.

Production career, worker, keys, registry and bridge configuration were not
accessed or modified. Existing 2027 gameplay and earlier DEV formats retain
their behavior. No merge, deployment or official activation is authorized.
