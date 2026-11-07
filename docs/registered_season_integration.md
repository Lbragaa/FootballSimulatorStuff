# Registered season continuation — PR #11 candidate

This branch adds `season-forward-lineage-3` to the existing lineage registry,
signer, career seed, parent claims, atomic accepted-head publication and phone
protocol. It is not installed, merged, activated or approved for the real career.
PR #11 still depends on PR #10. The original DEV profiles remain nonpromotable.

## Execution and approvals

`season_lineage.prepare` authenticates the actual accepted parent. A transition
requires completed/archived football, settled obligations and revealed narration.
The manifest binds the exact parent/database, generation, authority epoch,
existing seed hash, versioned model policy and deterministic operation program.
No new seed can be supplied. There is one shared parent claim, including across
legacy and season executors. Existing pending TEST reviews can only be superseded
by a separate explicit signed transition which retains the original review hash.

The same existing human confirmation gate handles three distinct decisions:
authorize the exact manifest, execute it once, accept its exact candidate hash.
The bridge signs only after the pinned human's original authenticated proof has
been durably recorded. Ordinary automatic gameplay cannot authorize a transition.
Approval of 2028 separately permits its bounded chronological gameplay; it does
not approve 2029. Revoking automatic mode continues to stop future advancement.

Initial setup includes the full offseason and January ACCESS bootstrap football
needed to determine the new league participants. This scope is disclosed in the
review. The later-season setup prepares offseason/calendar without playing it.
Repeated IDs resume original statements, destinations, results and acceptance.

## Storage and verification

Accepted payloads contain small immutable descriptors, not another full raw DB.
64 KiB content-addressed compressed chunks and 64-way Merkle page indexes share
unchanged bytes between every successor. The authority keeps one materialized
head; only owned scratch copies and older materializations are cleaned up.
The exact completed 2027 anchor, archive, receipts and historical chunks remain.

Each candidate reconstructs its exported state independently, authenticates the
immediate parent's signed history and exact file bytes, verifies the operation
chain/schema/protected history, replays the newly authorized program, and compares
every table. Acceptance independently repeats this validation. The trusted signer
attests the previous acceptance; this is not a cached validation flag. Full
history replay remains available, including the legacy anchor, via
`season_lineage.restore(..., full_audit=True)`.

Portable exports include reachable chunks and the signed lineage. Backup/recovery
reuse the original authority fencing and explicit lost-authority acknowledgment;
neither includes the signing key. A backup is not another active writer.
An operator copying a registry AND its signing key remains a trusted-operator
boundary, as in the existing authority. This is not distributed consensus.

## Phone commands in this candidate

The existing `braga-bridge-2` envelope, UUIDs, sequence, pinned identities, signed
replies and narration page IDs are unchanged. New control commands:

| Command | Exact args |
|---|---|
| `prepare_season_transition` | `{"policy":"supported-ecosystem-proposal-1"}` |
| `inspect_season_transition` | `{"preparation_id":"<UUID>"}` |
| `request_authorize_season` | `{"preparation_id":"<UUID>","manifest_sha256":"<hash>"}` |
| `request_execute_season` | same manifest args |
| `request_accept_season` | `{"preparation_id":"<UUID>","checkpoint_sha256":"<hash>"}` |

Each request command returns the existing exact-action human challenge. Nothing
in an ordinary issue body is human approval. These commands must not be sent to
the installed production worker until a separately authorized deployment.

`play_next_episode` subsequently delivers recorded offseason news, autonomous
lineups, chronological commentary, final whistle, results and standings using the
existing ordered presentation. Edition fixture keys are accepted by protocol 2
only; frozen protocol 1 is unchanged. `historical_results` reads accepted records
across seasons without simulation or cursor consumption. Older pinned history
pages reconstruct temporary snapshots and discard them after the read.

## Material proposals still requiring commissioner decisions

- Missing 2027 Série B: prospective ACCESS admission, never invented 2027 scores.
- Missing foreign national standings: explicit administrative country entry order.
- Missing country of a defending champion: additive forward declaration, preserving
  the inherited unknown value. The ambiguous Universidad Católica label denotes
  Chile only under this proposed mapping. The real Chilean club's existence is
  documented by [ANFP](https://www.anfp.cl/clubes/universidad-catolica/); this does
  not establish the fictional archive's intended identity.
- Initial state/federation CDB entries remain proposed registrations. Repeat CDB
  uses recorded previous cup finishes for 108 places plus 20 current Série A
  clubs under `domestic-cup-continuity-proposal-2`. This bounded alternative is not
  claimed to reproduce missing non-RJ state or regional championship results.
- Modeled ages, youth, retirement, guaranteed contracts and hypothetical club
  economics remain the disclosed offseason proposal. No unknown real revenue,
  opening capital or unrestricted Vasco transfer budget is asserted.
- Calendar, venues and international windows are the committed fictional proposal;
  rest/venue/dependency conflicts fail rather than weakening constraints.

## Verification status

The focused registered authority/Worker2 integration exercised migration,
execution interruption, invalid signature rejection, acceptance interruption,
recovery, a complete Vasco episode, exact retry and independent portable restore.
Its domain assertions passed. An initial Windows fixture-cleanup error was
isolated to readonly OneDrive directories; owned cleanup now handles that case.
Small chunk-corruption, deduplication and country-preservation tests passed.

The complete registered rehearsal now passed: 1,341 fixtures across 14 editions
in 2028, a second accepted transition/offseason and 27 completed 2029 fixtures.
Portable restoration and a separate full-history audit both passed. See the
[final evidence report](final_multiseason_integration_report.md) for counts,
timings, storage, exact coverage and outstanding activation decisions.
The runner uses the actual authority and Worker2 protocol with disconnected TEST
transport and public TEST credentials. It does not claim a new live iPhone test.
Safe numerical evidence is committed under `docs/validation/registered_*`;
raw databases/registries/keys are not. No production readiness/activation is
implied by the successful TEST run.
