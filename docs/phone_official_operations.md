# Task 04C proposed phone control procedure

Status: implemented in the opt-in v2 worker; live control rehearsal pending.
It remains disabled in the frozen v1 worker.
This is not authorization to provision a production authority or run a match.
The official world remains 046C v2, 2027-09-26 23:30.

## Separate human consent

An issue created by ChatGPT through the commissioner's GitHub connection has the
commissioner's GitHub identity. That proves transport access, not that the human
separately confirmed an exact irreversible action. A second assistant-created
issue, a generic “yes”, or having the worker sign its own request does not solve
that distinction.

The proposed minimal additional step uses the GitHub mobile app/browser and an
independently enrolled phone authenticator. The worker returns an exact-action
challenge on the private command issue. The human reviews the action and hashes,
opens that issue directly, and posts:

```text
BRAGA_CONFIRM_V1 <challenge UUID> <binding SHA256> <six-digit authenticator code>
```

Do not give an authenticator secret, production signing key or PAT to ChatGPT.
Enter the ephemeral code directly on the private GitHub issue; the bridge does
not echo it. GitHub retains the comment, including this short-lived code. It is
single use, bound to the challenge's exact issue/action/hash and expires. Never
use a code from an authenticator shared with another service. The Hikari client
must not interpret this comment as an ordinary engine result.

The runtime checks the pinned repository ID, human numeric ID/login, unedited
comment metadata, challenge binding, 10-minute expiry and a separately enrolled
RFC 6238 authenticator. GitHub App-generated confirmations are refused. A global
10-attempt limit per 10-minute window bounds online guessing across new
challenges. A code counter cannot authorize a second action. Only **one active
challenge per career** is allowed: finish/resume it before creating another.
This restriction matters because an ordinary TOTP does not cryptographically
encode the transaction hash. Without it, an assistant that sees a human's GitHub
comment could try copying the code to a different pending action. Completed
actions consume the counter; expired, unconfirmed challenges can be replaced,
while committed operations must resume their original receipts. Enrollment is
one-time trusted local setup; the authenticator's clock must remain reasonably
accurate. The shared authenticator secret also belongs to the trusted runtime:
this protects against assistant-created requests, not a compromised runtime or
malicious operator with local keys. GitHub account authentication remains the
remote transport trust boundary. Normal ChatGPT cannot independently verify the
runtime's HMAC without the local key.

`bridge.approval.HumanGate` stores its proof before calling the authority. A
crashed action resumes from that proof and its original lineage receipts; it does
not ask for another code, change the batch or select another seed. Lost or
tampered gate databases fail closed. Back up the gate with the stopped worker's
other private journals; never reset it to resolve a replay refusal.

## Distinct stages

1. **Prepare.** Resolve the exact immediate accepted parent and chronological
   boundary. Store the manifest locally. Return fixture IDs, payroll obligations,
   versions, seed-policy commitment hash and manifest SHA256. No match executes.
2. **Authorize.** Return an authorization challenge for that exact manifest. Only
   after the human confirmation does the runtime use the existing
   `lineage.expected_authorization` / `lineage.authorize` signature process.
   Existing parent/fixture/obligation claims fence competing requests.
3. **Execute.** A different exact-action challenge requires another human
   confirmation. Invoke `lineage.execute` with the already authorized execution
   ID and its locally derived output directory. Retries resume its commitments
   and cached results. This does not accept the candidate.
4. **Verify.** Independently replay the candidate and compare its registered
   checkpoint/archive hashes. The existing executor independently restores its
   exported archive before registering a candidate. Show validation and hashes,
   not unrevealed results, raw databases or diagnostic reports.
5. **Accept.** Return a third challenge bound to the exact validated candidate,
   archive hash, parent and manifest. Only the separate human confirmation permits
   `lineage.acceptance_template` / `lineage.accept`. Recover interrupted receipt
   publication with `lineage.recover_acceptance`, never a second acceptance.
6. **Narrate.** Deliver stored signed pages using the existing narration API. Read
   and narration privileges do not confer any of the control privileges above.

The local controls are `bridge-control-2`, separate from `braga-bridge-1`.
They require an existing matching active lineage authority, explicit local enable
flag and an exact signed local policy/control receipt. Production additionally
requires explicit local production binding. Provisional football-policy approval
in Task 04C is not that receipt, a career seed commitment, an execution approval
or acceptance of a successor. These modules do not provision any authority.

Task 04B's real mobile acceptance and merge are complete. The v2 worker and
closed schemas are implemented; see [the protocol](bridge_protocol_v2.md) and
[Hikari procedure](bridge_hikari_v2.md). Live v2 enrollment/control rehearsal is
still a separate acceptance gate. The frozen v1 installation has no control
commands; do not describe the earlier local simulated rehearsal as phone consent.

## One-time TEST-only rehearsal enrollment

A fresh isolated `output/task04c-phone-test/config.json` has been prepared with
TEST-only authority, a new private TEST signing key, fixed precommitted TEST seed,
and an empty, explicitly new bridge inbox. The earlier Task 04B career/ledger
remains intact. This new namespace is for the required from-root control test,
not a reset or reroll of that earlier career.

The human runs the following **in their own interactive PowerShell**. Never run
enrollment through an assistant tool or capture its private output into chat:

```powershell
.\output\task04c-runtime\Scripts\python.exe -I -m braga_era.bridge.setup_test enroll --config output/task04c-phone-test/config.json --confirm-test-enrollment
```

Add the displayed setup key to a phone authenticator as a time-based Braga TEST
ONLY account (SHA1, six digits, 30 seconds), then enter its current code at the
hidden local prompt. Keep the setup key and code out of chat, screenshots, GitHub
and logs. Enrollment verifies possession before enabling TEST control review.
It does not authorize/execute a batch or accept a successor. A lost established
inbox/gate/store is refused, not recreated. Interrupted initial enrollment can
resume the same secret and already-created journals.

For a genuinely new local rehearsal only:

```text
python -m braga_era.bridge.setup_test create --db EXACT_ACCEPTED_DB --directory NEW_TEST_DIRECTORY
```

This supports only TEST-only provisioning. It refuses an existing output and
never touches the real accepted registry. Production setup is not an option.

## Roundups and compact delivery

`bridge.roundup.Roundups` accepts an explicit bounded subset of the earliest
simultaneous narration group, plus matches held for detailed commentary. Only
stored eligible results can be consumed. Stable signed narration page IDs are
used in chunks of 20 events; journals retain page hashes and final summaries.
The response contains scores only after the corresponding final page has been
consumed. A repeated request returns its original summary. A crash after a page
but before journal persistence retrieves that exact cached page.

The user chooses detailed matches before accepting a roundup of the rest. Held
matches remain the next eligible events; the roundup cannot jump to a later
kickoff, simulate a result or automatically summarize Vasco. Hikari must continue
earlier commitments before reaching Mirassol–Vasco. History, accepted checkpoint
bytes and canonical event representations remain unchanged.

`compact_events` is a lossless presentation projection. Each distinct on-field
identity array pair appears once per delivery under a SHA256 reference; events
refer to it. `expand_events` verifies and reconstructs the precise arrays. Player
names remain available through the prematch identity mapping. Existing engine
events, signed lineage pages and earlier bridge replies are not rewritten.

## One-time local production checklist — instructions only

- Finish the real iPhone command/reply test with a repository-scoped PAT in
  Windows Credential Manager; verify restart/resume without resetting the ledger.
- Review and merge Task 04B only after that test. Review the separate Task 04C
  implementation and its actual phone-only rehearsal before enabling controls.
- Install a reviewed runtime in a stable Windows location. Keep one active worker
  per career; optionally enable login startup only after explicit human opt-in.
  Sleep/offline PCs queue commands until they resume. No cloud host is required.
- Separately authorize creation of a production signing key, protect its local
  file and keep private recovery backups external to saves, GitHub and chat.
- Separately authorize one production authority registry, exact root installation
  and once-only career seed commitment. Test-only registries cannot become
  production. Use the existing fencing/backup/transfer procedure.
- Review the proposed model/policy bundle and create its exact local signed
  policy/control receipt only after a separate human decision.
- Separately enroll the human authenticator directly into a phone authenticator
  app and protected runtime storage. Keep the enrollment secret out of GitHub,
  ChatGPT, logs, source control and save packages. This task has not performed
  production enrollment.
- Explicitly bind the approved production authority, human numeric identity,
  private repository and local journals. Scope read/narration independently from
  control requests. Back up the stopped worker's journals with career backups.
- Prepare and review the first exact batch: eight LIB R16 first legs, eight SULA
  playoff first legs, September incremental payroll once, and no R26 fixture.
- Obtain separate exact-manifest authorization and execution confirmations. After
  independent candidate verification obtain a separate exact-hash acceptance.
  The setup steps above authorize none of these actions.

No official Save 047, production seed, signing key, acceptance or fictional-time
advance is created by these instructions or the local TEST-ONLY rehearsal.
