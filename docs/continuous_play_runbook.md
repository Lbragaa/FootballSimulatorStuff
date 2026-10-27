# Continuous Hikari play — profile 2

**No production provisioning or official execution is authorized by Task 03D.**
Original 046 and accepted 046C v2 remain immutable. The accepted official date is
2027-09-26 23:30. This runbook describes the separate workflow that a later
commissioner instruction may authorize.

## Runtime and trust

Use Python 3.11–3.13 and package 0.7.0, installed from this repository/wheel. Runtime
uses the standard library. ChatGPT needs a trusted local Python executor or an
explicit file exchange with a Python-capable environment. The GitHub connector
can inspect code; it cannot run local Python or mutate SQLite.

There is **one writable authority registry per career**. A raw signing key of at
least 32 cryptographically random bytes belongs to the commissioner/operator,
outside Git history, save archives and Hikari's ordinary context. Do not paste
the key into chat. The local worker reads a protected key file; Hikari receives
structured outputs and signed receipts, not the secret.

Task 03D creates only TEST-ONLY registries using a public simulated test key. Such
signatures prove the rehearsal mechanism, not independent commissioner approval.
Production key/authority provisioning requires a new explicit instruction.

The registered `continuous-forward-lineage-2` profile authenticates each immediate
accepted parent. It does not accept arbitrary SQLite files or relabeled DEV saves.
The embedded exact 046C root is historical evidence; generation two onward copies
the immediate parent and independently replays only the newly authorized delta.
Its initial roster and career seed are inherited, not regenerated per checkpoint.
All supported remaining-2027 batches use the same registered model/policies.
New season content or a changed model needs explicit versioned policy work.
Batch boundaries currently require a complete day at 23:59. Mid-match boundaries
are rejected; narration can still stop and resume at individual event pages.

## Copyable rehearsal

Install exact accepted root once:

```text
python tools/bootstrap_accepted.py --download --output output/accepted-046c
python -m braga_era inspect --db output/accepted-046c/database.sqlite
python -m braga_era audit --db output/accepted-046c/database.sqlite
python tools/rehearse_task03d.py --db output/accepted-046c/database.sqlite --output output/TEST-ONLY-continuous-rehearsal
```

The last command uses simulated signatures, accepts three **test** successors,
transfers the first one to another runtime directory, exercises a crash, preserves
narration sequences 1→2→3 and compares all football state with an uninterrupted
control world. It never changes the real accepted registry. Its ordinary output
omits future Vasco scores. `rehearsal.json` records exact hashes; the checkpoint
ZIPs contain private results and full provenance.

## Explicit commands for one batch

All commands below run in the trusted worker. Replace `KEY_FILE` with the opaque
path to an existing commissioner-controlled key, and `REGISTRY` with the single
active authority. The ordinary narrator must not receive the key's bytes.

For a rehearsal authority only:

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE init-rehearsal --career TEST-ONLY-career --seed fixed-before-any-results
```

That command cannot provision production authority. Production provisioning is an
explicit Python `lineage.provision(..., test_only=False, ...)` operation reserved
for a later authorized task and trusted human setup. The initial career seed is
committed once; later batch commands accept no replacement seed.

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE inspect
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE prepare --parent PARENT --until "2027-09-30 23:59" --execution-id BATCH1 --output batch1.json
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE authorization-template --manifest batch1.json --output execution-decision.json
```

`PARENT` is the exact accepted 046C database for generation one. For every later
batch it is the directory of the latest separately accepted lineage checkpoint.
Preparation identifies every earlier due fixture/obligation and does not execute.
Review [the policy bundle](task03d_decisions.md) and the exact manifest, including
seed policy, versions, boundary and payroll. A template is not approval.

Only after the human commissioner supplies the decision:

```text
python -m braga_era.continuous --key-file KEY_FILE sign-decision --decision execution-decision.json --output execution-approval.json
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE authorize --parent PARENT --manifest batch1.json --approval execution-approval.json
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE execute --execution-id BATCH1 --directory BATCH1_DIRECTORY
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE verify --checkpoint BATCH1_DIRECTORY
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE acceptance-template --checkpoint BATCH1_DIRECTORY --output successor-decision.json
```

Execution and acceptance are separate. Inspect the independent validation and exact
candidate/package hashes. The commissioner must supply the different successor
acceptance decision before these commands:

```text
python -m braga_era.continuous --key-file KEY_FILE sign-decision --decision successor-decision.json --output successor-approval.json
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE accept --checkpoint BATCH1_DIRECTORY --approval successor-approval.json
```

Software/policy acceptance alone cannot authorize a match. An assistant-generated
HMAC is not independent commissioner consent. The worker must act on the human's
reviewed decision, not invent approval text and treat its own signature as consent.
No public official save number is assigned by these examples. Accepted generation
numbers are chronological checkpoints, independent of league-round numbers.

## Next episode and crash resumption

For batch two, use the accepted batch-one directory as `PARENT`, a new execution
ID and boundary **2027-10-03 23:59**. It contains all ten R26 fixtures, including
the protected Mirassol–Vasco kickoff. For batch three, use accepted batch two and
boundary **2027-10-06 23:59**, including all 16 return legs. Repeat the same distinct
prepare → human authorization → execute → verify → human acceptance steps.

Do not return to 046C or create a new seed for later episodes. The registry rejects
stale/unaccepted parents, already claimed fixtures, competing parent claims and
replayed acceptance. Existing results, draw commitments, medical state, form,
discipline and finance carry in the immediate-parent database.

After an execution crash, run the **same execute command**, execution ID and output
directory. Input/seed commitments and cached results survive; failed applications
roll back. Never delete the registry/claims or restart the career to obtain another
outcome. Export/validation failures resume from the stored world. If acceptance
committed but its external receipt file was interrupted, use:

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE recover-acceptance --checkpoint BATCH_DIRECTORY
```

This restores the already registered signed receipt; it does not accept twice.

## Narration is separate from computed football

The accepted database may already contain 16 continental results. Hikari is not
allowed to reveal them merely because they are computed. `inspect` reports the
accepted football clock and next due calendar entries. `play next` identifies the
earliest unrevealed narration group. They can refer to different dates.

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE play next
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE play preview --fixture lib:LIB-R16-01:L1
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE play narrate --fixture lib:LIB-R16-01:L1 --count 1 --page-id CAREER-MATCH-PAGE001
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE play table
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE play finances
```

Use a stable page request ID when retrying after an interruption. Repeating that
ID returns the same saved response; a different request under the same ID is
rejected. Use a new ID for the next page. For “continue to halftime”, request one
event at a time and stop at `HALF_TIME`; larger pages can cross a boundary.

Previews cannot jump past earlier unrevealed matches. Shot outcomes are withheld
until their own events; postmatch statistics unlock at the final whistle. Tables
are rebuilt from revealed finals, not from sealed future results. Narration writes
only a private session copy and a signed cursor/delivery ledger. Accepted checkpoint
bytes remain immutable. Cursor state and responses are authenticated, and carry
across accepted successors without affecting match seeds.

## Transfer, backups and key recovery

Normal backup:

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE backup --output BACKUP_DIRECTORY
```

It contains the accepted head ZIP, signed acceptance, signed cursor and an authority
snapshot with no signing key. A normal backup is inactive and requires explicit
lost-authority recovery before activation. Finish/recover any pending authorized
batch before backing up the accepted head.

For an intentional machine transfer:

```text
python -m braga_era.continuous --registry REGISTRY --key-file KEY_FILE backup --transfer --output TRANSFER_DIRECTORY
python -m braga_era.continuous --key-file KEY_FILE restore-backup --input TRANSFER_DIRECTORY --output NEW_RUNTIME_DIRECTORY --test-only
```

`--test-only` is correct for every Task 03D artifact. A future production transfer
must explicitly select `--production`; it rejects a test-only bundle. Transfer
fences the original writer before publishing its handoff. A failed publication
can retry only its original transfer destination. The restored runtime authenticates
the package/lineage, relocates runtime paths and resumes the signed narration
cursor. No original handoff directory or external 046C installation is needed
after an accepted parent is portable; the exact historical root is embedded.

For disaster recovery, first retire/fence the old writer, then restore a normal
backup with the additional `--recover-lost-authority` flag. This is an explicit
operator recovery assertion, not a new match authorization. Never activate two
copies of a career. A filesystem registry is not a distributed consensus service:
an operator controlling the key must not clone offline writers or roll back an old
authority snapshot to fork history. Unique claims, parent/head CAS and fencing
protect normal operation within the designated authority.

Keep two encrypted/offline key backups, separately from save/authority backups.
Check the key fingerprint before use. Losing the key does not justify generating
a replacement key, re-signing an invented past, deleting claims or choosing new
seeds. Recover the exact key; if no copy exists, stop for explicit commissioner
trust-recovery work. Routine Hikari handoffs contain no secret key.

## Copyable new-conversation handoff

> THE BRAGA ERA: use continuous-forward-lineage-2 and the attached portable accepted
> checkpoint/authority handoff plus signed narration cursor. This is [TEST-ONLY or
> explicitly commissioner-accepted production; verify the actual flag]. Authenticate
> the exact accepted head and immediate parent before preparing a batch. The trusted
> local worker has the signing key outside this chat; the GitHub connector cannot
> execute SQLite. Show `inspect` and `play next`. Resume narration with stored page
> IDs/cursors; do not recalculate results, invent events or expose later fixtures.
> A new batch needs a reviewed manifest and separate human execution authorization;
> a successor needs separate exact-hash acceptance. Do not interpret this handoff
> itself as permission for a new official match.
