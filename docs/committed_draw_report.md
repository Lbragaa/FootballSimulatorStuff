# Committed group-draw correction

The suspected inconsistency was real. `schedule_country_groups` stored the
country-constrained groups in its signed operation response and fixture rows,
but `groups.pools()` could run the older unconstrained shuffle again for LIB.
The reconstructed membership could therefore differ from the actual draw.
Existing group tables calculated from stored fixtures; this finding alone is
not evidence that previous scores, tables or qualifiers were incorrect.

The public pool reader now returns the committed country-draw receipt and
cross-checks it against the complete fixture inventory. Legacy generic draws
use their stored fixtures, preserving old operation responses and replay.
An uncommitted draw cannot be inspected as if it had taken place. The original
generic shuffle is private to initial scheduling, with its seed inputs unchanged.
Tables, qualification paths, SULA cross-entry/bye logic and historical reporting
use or validate that same recorded membership. No results are regenerated.

Validation rejects clubs in multiple groups, duplicate members, self-matches,
missing/duplicate ordered pairings and receipt/fixture disagreement. Operation
authentication remains the existing signed store/accepted-package boundary;
the read-only membership helper does not substitute for signature verification.
There is no new schema or second draw archive.

## Disconnected evidence

`tests/test_committed_groups.py` registers 32 explicitly fictional test clubs
across four known modeled countries. Their separate country-registration command
retains the old Brazilian registration's identities and provenance unchanged.
No existing club's missing nationality is filled in or relabeled.

The test commits a constrained eight-group draw, interrupts after transaction
commit, retries the same request ID twice, simulates all 96 group fixtures with
the real engine and shared player state, then checks all table/qualifier
memberships before and after export and independent restoration. Additional
negative cases reject inconsistent receipts, tables and historical projections.
These synthetic entries are explicitly a draw regression scenario, **not**
evidence of national qualification or a full continental entry rehearsal.

Local verification passed the 23-test draw/group/historical selection, the five
negative reader cases, and the existing 266-match main-stage replay/export/restore
test (264.32 seconds). Test timings include local concurrent test workloads and
are not before/after performance comparisons. All six protected root/artifact
SHA256 values matched their recorded values. The prior head `4a51f87` passed
[six-platform CI](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/41082632736);
new-head CI must be checked separately.

## Scope and remaining integration

This correction completes the group-draw audit. It does not join the earlier
30-match preliminary and 266-match main-stage rehearsals into one complete
country-qualification-to-finals run. Missing authenticated national qualification
inputs and the versioned scenario/evidence interface remain the next entry
integration work. Full domestic calendars, complete Copa do Brasil/state/Série B
formats, comprehensive autonomous offseason, repeated 2029 play and season-aware
production authority/bridge remain incomplete. The system is **not 2028-ready**.

No new performance gain is claimed. The previous 7.04% verified-pipeline and
17.9% team-loading measurements remain separate earlier evidence, not an
episode-latency result from this correction. Production career, worker,
credentials, registry, accepted checkpoints and official clock were untouched.
