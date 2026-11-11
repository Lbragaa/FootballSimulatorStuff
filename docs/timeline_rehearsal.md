# Career rewind rehearsal

The registered season history retains signed checkpoint descriptors and
content-addressed database chunks. The source of the 2028 Libertadores rewind
is `c090fe185089a5fc5a1cf0a748a532ac499dba5abe204fa5282988a54ab68136`,
generation 14, April 9 at 17:33 in the career. The first Libertadores group
kickoff was April 12 at 16:00. Issue #120 completed at the June 18 head, 16
successors and 408 matches after the rewind point. This includes 90 Série A,
90 Série B, 36 lower-division, 32 Copa do Brasil, 80 Libertadores and 80
Sul-Americana matches. The accepted April 9 state preserves every earlier
result and roster, economic and competition record. Later fixtures are
interdependent and belong to their respective timelines.

## Implemented

- `multiseason.timeline.accepted_history` reads signed registered checkpoint
  identities, career time and local descriptor availability. A descriptor
  alone does not guarantee the corresponding archive objects still exist.
- `bookmark` writes a signed name and description bound to an exact accepted
  package. It is a reference and requires the existing archive to restore.
- `rehearse` authenticates the registered source, independently materializes
  its exact database and creates a new signed, nonpromotable TEST branch.
  It requires a separate signer and an explicit same or alternate seed mode.
  The distinct alternate seed is committed before any replay. The inherited
  entropy parent is preserved for same-seed compatibility.
- New rehearsal operations keep the normal transactional operation journal
  and match engine. Independent replay starts from the original accepted
  database and verifies the complete resulting tables. A fresh signed archive
  preserves the verified branch and checks the hash of each member.

The isolated same-seed check matched 32 result digests from the original
first kickoff group. The first alternate branch finished first in Group 8,
earning a Libertadores knockout berth. This branch has no production
acceptance receipt. The original career and its sealed bridge ledger remain
the active route.

Run the targeted rehearsal with `python -m tools.rehearse_libertadores_rewind`
and a locally secured empty directory. The config identifies the signed source
authority and is read-only. Resuming uses the same branch directory and seed
mode. Keep private keys separate from portable archives and out of GitHub.

## Production integration boundary

The registered qualifying import is pinned to the exact independently replayed
Libertadores archive. The production import verifies the source package,
archive members, replay attestation, Group 8 result and original seed before
creating a distinct signer and registry. It registers the saved June 28
database as an immutable source and verifies that only authority metadata
changes in the operational copy. It does not replay the matches again.
The imported cursor seal covers results through the April 9 fork point.
Replayed matches after that point remain available for chronological narration.
Full league tables wait while any accepted league results remain unrevealed.
The original Episode #81 import still accepts only its own reviewed archive.

A live switch needs a sealed idle-state proof, a verified archive and rollback
route, a new branch ledger and career identity, and a single worker binding.
Test interrupted registration and switching, stale issues, restart and
switch-back before replacing the scheduled worker. Archive, restore and
timeline changes need explicit authorization outside ordinary gameplay.
The read-only history and bookmarks are local APIs in this branch. General
bridge commands for save discovery, naming and arbitrary timeline switching
remain separate from this exact one-time cutover.
