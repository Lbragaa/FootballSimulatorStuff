# Task 03D — continuous play and final policy review

**TEST-ONLY, NONCANONICAL.** No official fixture, official successor, production
authority/key, real-registry change or canonical time advance is authorized or
performed. Accepted 046C v2 remains September 26, 2027 at 23:30; Vasco 3–2
Palmeiras is final; Vasco remains ninth with 38 points after 25 games; the protected
Mirassol away fixture remains officially unplayed.

## Consolidation

PR #6 was verified at exact expected head
`3ac9a8315b2e5c472492888104b38a8967683897`, against main
`7a145b98ffc6096d42423d0ea9219dac1cad8e75`. Its two commits, protected-file scope,
ancestry and mergeability matched the Task 03C candidate. Run `40589578593`
passed six Windows/Linux Python 3.11–3.13 jobs, 210 tests each, the old engine/world
regressions and identical full-season fingerprint. It was ordinarily merged as
`f9e7538ed0344d5948290c90d2fcf6326be5dcc0`, preserving history.

Resulting-main run `40596052780` passed all six jobs. The unchanged local baseline
passed **210 tests in 482.79 seconds**. Work uses the single branch
`codex/task-03d-continuous-play`; its PR is left open, with no force-push or
automatic merge. Package version is 0.7.0.

## Registered immediate-parent progression

`braga_era.lineage` adds `continuous-forward-lineage-2` over the existing world
executor, validators, adapters and player timeline. Task 03C's profile and every
previous engine/world regression remain supported. This is a control-plane
extension, not a replacement football engine.

Each successor binds the exact immediate accepted checkpoint hash **and database
hash**, package identity, root, generation, career, policy/configuration versions,
immutable seed policy, exact new fixture/obligation inventory and operation-chain
tail. The registry verifies signed execution, independent-validation and separate
acceptance receipts. An unaccepted, stale, unrelated, development-only, tampered
or wrong-mode parent fails closed. Every accepted parent already has its own
independently validated package and signed lineage proof.

The first generation authenticates exact 046C bytes. Later execution **copies its
immediate accepted parent**, retaining events, fixtures, players, injuries,
discipline, form, finances, draws and coach inputs. It does not reconstruct squads
or simulate old fixtures. Independent successor verification starts from the
embedded immediate-parent snapshot and replays only that successor's delta.
The embedded exact 046C file remains a permanent historical reference for full
journal/history audits; there is no dependency on its original installation path.

The career seed is committed before the first draw and inherited under
`career-stable-per-fixture-1`. A batch/execution ID is not a new RNG namespace.
Existing fixture snapshot/configuration/seed commitments remain unchanged;
global fixture claims cannot be reacquired under another ID or parent. A single
parent can have only one authorized continuation; acceptance also uses unique
parent constraints and a transactional head compare-and-swap. No generic raw-DB
or arbitrary-parent acceptance bypass is introduced.

## Three-checkpoint rehearsal

The reproducible command is:

```text
python tools/rehearse_task03d.py --db output/Save046C_v2/database.sqlite --output output/TEST-ONLY-task03d
```

It uses only a public simulated test key and disposable registry. The fixed seed
was named before outcomes; no Vasco outcome is used to choose a seed.

| Generation | Authorized boundary | New fixtures | Total completed forward fixtures | Administrative consequence |
|---|---|---:|---:|---|
| 1 | September 30, 23:59 | 16 continental first legs | 16 | September payroll exactly once |
| 2 | October 3, 23:59 | All ten R26 league games | 26 | Inherits September settlement; no repost |
| 3 | October 6, 23:59 | All 16 continental returns | 42 | Aggregates/qualifiers and subsequent committed draws retained |

The accepted football clock is the last actual event/completion or obligation,
not an invented advance to the requested boundary. These test save generations
are chronological checkpoints, not league-round numbers or an official Save 047.

Every candidate independently restores/verifies before its separate **test**
acceptance. The rehearsal transfers the first accepted checkpoint/authority to
another runtime directory and continues from that parent. It exercises a durable
post-result crash on batch two. Narration emits sequences 1, 2 and 3 across the
three generations; repeated page IDs return the same stored response.

The final logical football fingerprint equals an independently simulated single
world using the same career/fixture commitments:

`5e1ed0d03c3c5f3d9cce25b043ff8bd33cb296df903a09da1d113d2003dd3151`.

The comparison includes receipts, input snapshots, committed seeds, results,
events, player state, competition/standings, financial rows and operation chains.
Only the explicitly separate narration cursor is excluded from football identity.
Machine-readable evidence records exact per-generation checkpoint, parent, DB and
archive hashes; physical SQLite/ZIP identity is not claimed identical across
platform builds. Semantic identity and each actual package's hashes are verified.

The fixed 42-match path has forward suspensions; its return-leg snapshots prove
that prior competition bans exclude players. No new injury happened in that path.
Controlled temporary injury/fitness/morale/form/ban copy-and-recovery tests cover
that transport case without manufacturing an injury in an accepted rehearsal.
Earlier Task 03C long-season injury evidence remains preserved.

## Portability, immutable bytes and recovery

The new format-2 package contains the current snapshot, exact immediate parent,
fixed historical root, signed provenance chain, authorization, validation and
narration snapshot. It never nests prior ZIPs. Its explicit 256 MB bound allows
the two adjacent football snapshots; the original format-1 100 MB limit and frozen
profiles are unchanged. Growth is linear in retained world data rather than
recursive archive nesting. A future season exceeding this registered bound needs
an explicit archival/profile decision, not a silently increased limit.

Registry configuration, cursor state and delivered pages are authenticated.
Accepted checkpoint files never receive narration writes: a checked session copy
and signed cursor/delivery ledger handle reveal progress. A page ID binds its
request and response, so an interrupted delivery can be retried without advancing
again or recomputing a result. Invalid/rewound cursors and modified working state
are rejected. Football completion and Hikari reveal completion remain distinct.

Candidate/export crashes keep original commitments and cached results. Acceptance
and the head pointer commit together; failed acceptance rolls back completely.
If the commit succeeds but external receipt publication is interrupted,
`recover-acceptance` restores the registered exact signed receipt. Repeated
acceptance is safely rejected without moving the head.

Portable accepted-career handoffs carry the registry/claims, latest package,
accepted lineage and signed cursor, **never the key**. Transfer fences the old
writer before publishing the handoff; the restored runtime validates mode/hash/
signatures and relocates paths. Normal backups require explicit lost-authority
recovery before activation. Tests reject rehearsal→production conversion.

One active trusted authority is the operational trust boundary. A portable SQLite
registry is not distributed consensus against an operator who controls the key
and deliberately clones or rolls back offline copies. Stop/fence the old writer
and activate a transfer once. This limitation is explicit, not an assertion that
cryptographic signatures alone prevent a malicious owner from forking authority.

An observed Windows export descriptor problem was fixed by flushing a writable
temporary archive handle. An observed transient directory-rename denial now has
bounded retries in the new lineage publisher; original publisher behavior remains
the default. Neither fix changes seed commitments or validation rules.

## Targeted realism findings

The original 1,200-trial finding is reproduced exactly: 81 straight reds plus 225
second-yellow dismissals, 306 total, in 272 matches. Position-weighted repeat
cautions explain most dismissals. Lowering straight reds alone does not remove
that interaction; other preregistered alternatives also reduce caution volume.
No reliable fictional historical red/injury series establishes a replacement rate.
The current model is retained, with that uncertainty explicitly requiring approval.

New identical-team controls isolate home advantage: home/draw/away
43.0/30.0/27.0%, and reversed identities 46.3/27.0/26.7%, with about ±5.7 pp maximum
95% sampling half-width for 300 trials/cell. Club-strength-only, player-quality-only,
small/large gaps and symmetric/opposed tactics are separately tested. A 15-point
combined quality gap produces 84.3% home wins in the controlled scenario; it is
not the old mixed-roster gap-zero experiment. The effect follows documented
quality/finishing terms, with no hidden Vasco adjustment.

Fitness selection .12 changes an actual controlled XI choice that .05 does not;
suspensions override selection under both settings. A 24-match congestion control
exposes deep-squad rotation and fitness-ceiling behavior. This bounds model
semantics rather than claiming medical realism. No probability, recovery or
managerial rule is changed without justified versioned evidence.

See [policy decisions](task03d_decisions.md) and the numerical calibration JSON.
Aggregate-aware management is not added: coaches react to match score. Accept
that stated simplification or require a new forward configuration before affected
return-leg authorization. Tie/aggregate resolution itself is implemented and tested.

## Explicit readiness answers

1. **Can the engine continue from accepted future saves?** Yes, for the supported
   2027 agenda through repeated registered profile-2 successors. Each immediate
   accepted parent is authenticated; no per-parent code/catalog edit is needed.
   This does not invent a 2028 calendar or unapproved future model.
2. **Can it resume after a crash without rerolling?** Yes. Original inputs, seeds
   and cached results survive; execution, export and acceptance failures are
   covered, with rollback and signed receipt recovery.
3. **Can Hikari narrate stored results without spoilers?** Yes through the trusted
   `continuous play` interface and signed cursors/page receipts. Private DB/ZIP/
   diagnostics are not normal narrator inputs.
4. **Are unusual card/strength findings resolved?** Their mechanisms and numerical
   bounds are identified. Empirical football-policy acceptance remains unresolved
   because the source cannot establish the missing rare-event rates. No tuning
   for desired Vasco outcomes is performed.
5. **Which policies still need approval?** The exact bundle in
   `task03d_decisions.md`: foreign priors/unknown history, engine, injuries/cards,
   discipline, recovery/form, tiebreaks/ET, draws/home ordering, neutral finals,
   managerial scope, finance restrictions and seed/authority policy.
6. **Is September 30 technically ready for separate authorization?** The test-only
   complete gate is demonstrated. Production remains blocked on those human
   decisions and a new explicit provisioning/execution instruction; nothing in
   this report supplies it.
7. **What runtime/key/handoff is required?** Python 3.11–3.13/package 0.7.0, one
   trusted active registry, an external commissioner-controlled raw key and the
   portable accepted-career package plus signed cursor. The GitHub connector
   alone cannot execute local SQLite. See the copyable runbook.
8. **Any technical blocker to Mirassol after batch one?** The profile-2 rehearsal
   executes/restores/accepts that exact next batch from generation one and carries
   its prior state. It still needs its own explicit authorization and acceptance;
   approval of September 30 does not authorize October 3.

## Deliverables and evidence

- [Continuous-play runbook](continuous_play_runbook.md): exact commands, conversation
  handoff, key backup/recovery, transfer fencing and page-resume procedure.
- [First official manifest template](first_official_batch_manifest.md): exact 16
  fixtures and September obligation; explicitly unsigned and unapproved.
- [Commissioner decision bundle](task03d_decisions.md): retained assumptions and
  controlled alternatives, with no production acceptance.
- Validation evidence under `docs/validation/` and ignored `output/`; the Task 03D
  PR links final local/CI results. Binaries and keys are not committed as saves.

Stop state remains exact accepted 046C v2. No official Save 047 is created, named,
released or promoted; no official fixture is executed; the Task 03D PR remains
open for review. The next action belongs to the commissioner, not an automatic
match run inferred from passing tests.


## Final artifact verification

The final fresh three-generation rehearsal passed independent delta replay,
portable authority transfer, signed narration continuation and the uninterrupted
football fingerprint comparison. Exact local checkpoint/parent/database/archive
hashes and archive sizes are recorded in
[`task03d_artifacts.json`](validation/task03d_artifacts.json);
[`task03d_rehearsal.json`](validation/task03d_rehearsal.json) records the semantic
regression reference. Local archives are 3,485,913 / 5,475,320 / 6,631,017 bytes.
Physical hashes identify these artifacts; cross-platform CI compares semantic
world identity rather than manufacturing identical SQLite container bytes.

A built 0.7.0 wheel was installed to a separate import directory and run outside
the repository with Python site initialization disabled. Generation-one portable
authority/package restoration passed there without accessing an accepted-root
installation. The continuation regression also forbids root reinitialization and
external accepted-file reads after the portable first generation. Foundation
bootstrap, inspection, accepted-profile audit and package verification passed;
known historical warnings remain disclosed. All six protected ZIP/DB/approval/
registry hashes remained unchanged.

The initial 24 new continuation tests passed twice (637.26 and 637.77 seconds);
publication/CLI checks passed four focused tests after adding a real subprocess
death recovery case. The final full suite and six-platform CI results are linked
in the pull request; only completed runs are reported as passing.

New Task 03D database packages stay in ignored local output. CI publishes only
the spoiler-safe Task 03D rehearsal report. Automatic approval review rejected
adding these database copies to Actions uploads because that destination had not
been verified as trusted; no alternative binary upload was attempted. This does
not block local package production, independent restore or CI execution.
