# Joined continental entry-to-finals development proof

This extends PR #11 after the committed-draw correction. It is a disconnected
DEV-MULTISEASON-2 implementation, not an official policy, production migration
or declaration that 2028 is playable.

## Implemented entry and progression

`commit_continental_entry` commits exact `season`, `policy`, `national_evidence`
and `champions` inputs through the existing signed, transactional operation API.
Policy `continental-entry-development-1` validates persistent identities,
countries, source editions/title decisions, unique routes and replacement depth.
An exact request retry returns its original receipt; another intake cannot
replace existing season qualifications. All entry provenance remains in signed
operations and existing qualification/edition records, without a new schema.

Evidence supports completed adjacent-season edition tables, league-plus-cup
entry orders, recorded 2027 Brazilian league/cup results, recorded continental
champions, or explicitly named **unapproved development administrative scenarios**.
The last option supplies entry ordering, not fabricated historical scores.
Missing or contradictory facts fail closed. Foreign source tables are not
created by this interface. Cup-priority ordering and all allocations below are
versioned proposals requiring review before activation.

Both continental champions enter LIB groups directly. National routes exclude
those clubs and use remaining recorded/scenario depth, preventing overlapping
entries. LIB receives 28 direct group entrants, six PRE1 entrants and thirteen
PRE2 direct entrants. Actual PRE1 winners complete PRE2's sixteen; actual PRE2
winners enter PRE3; its four winners complete LIB's groups and four losers
transfer to SULA. New-intake LIB preliminaries use strength pots, seeded return
hosts, deterministic bounded country-constrained draws. Older DEV preliminary
operations retain their original draw behavior and receipts.

SULA receives twelve BRA/ARG direct entrants and 32 national-preliminary entrants
(four from each other country). Sixteen single matches pair clubs within each
country, with direct penalties on ties. Their sixteen actual winners plus four
LIB PRE3 losers complete the 32-club SULA groups. Eight LIB group thirds then
transfer into SULA playoffs; SULA group winners retain their byes. Existing main
stage adapters resolve both finals and retain champions and historical results.
No regulation engine probabilities, existing seeds or completed scores change.

## Actual joined rehearsal

| Edition/stage | Completed fixtures |
| --- | ---: |
| LIB PRE1 | 6 |
| LIB PRE2 | 16 |
| LIB PRE3 | 8 |
| SULA national preliminary | 16 |
| LIB groups / R16 / QF / SF / final | 96 / 16 / 8 / 4 / 1 |
| SULA groups / playoff / R16 / QF / SF / final | 96 / 16 / 16 / 8 / 4 / 1 |
| Total | **312** |

`tests/test_continental_integration.py` runs all six editions on one chronological
world, with shared player state, minimum rest and existing payroll obligations.
The parent is the standard authenticated completed-2027 NONCANONICAL test fixture,
not the live production career. Ninety-one explicitly fictional test clubs and
named administrative scenarios cover ten countries and title overlaps. Thus this
proves pipeline integration under declared inputs; it does not authenticate the
real career's missing foreign national qualification facts.
The mechanism test uses a compressed January–April calendar respecting the
existing rest/blackout checks; it is not the proposed full 2028 domestic and
continental calendar or an approval of continental finals in April.

The first complete selection passed 11 tests in 380.49 seconds, including all
312 matches, independent replay, export and restoration. Subsequent evidence
tests also checked read-only Brazilian league/cup projection. Negative cases
cover missing sources, duplicate titles/clubs, wrong countries, insufficient
replacement depth, unsupported policies and false historical title claims.
The existing 24-test preliminary/historical compatibility selection passed.
The final 12-test selection passed in 281.63 seconds, including an injected
crash after a main-stage simultaneous group committed, exact-request resumption,
unchanged prior result hashes/payroll and independent restoration. All 312
result hashes matched the uninterrupted run (aggregate commitment
`0c08200f9f02eb15ff345fced7c9adbfa0334bb9c9bfe35f52c683c90927951e`).
The worlds have different operation UUIDs and therefore different journal/world
hashes; no claim is made that those distinct journals have identical bytes.
Each database was 124,461,056 bytes and each portable directory 208,235,473 bytes.
Final-head cross-platform CI must be checked separately. The subsequent
[paired export benchmark](continental_export_performance.md) preserved every
portable byte while reducing the complete verification/export/restore workload.

## Remaining activation blockers

This is not the full requested shared domestic/continental 2028 world. Full Copa
do Brasil entry, state formats, reusable Série B, domestic calendar integration,
comprehensive autonomous offseason, repeated 2029 gameplay and season-aware
production authority/bridge still need implementation and a combined rehearsal.
LIB's main-stage knockout currently inherits the existing committed open draw;
group-winner-seeded LIB R16 pairing is not implemented. Country/pot restrictions
in this proof apply to preliminary/group draws, with SULA's existing winner byes
and R16 return-leg hosts retained. This proposed open LIB draw must be reviewed
or replaced by a new version before claiming a settled official format.
Actual foreign qualification evidence or explicitly accepted administrative
decisions remains required for the existing career. No scenario has been approved.
The rehearsal timings are not performance comparisons; the separate paired
benchmark provides the measured export improvement. No worker, authority, key, production
registry, accepted checkpoint or official fictional clock was modified.
