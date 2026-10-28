# Task 04C — phone operations and safe control

**In progress: v2 phone rehearsal and final CI remain acceptance gates.** No
production provisioning, official match, Save 047, official seed or canonical
clock advancement is authorized or performed. Accepted 046C v2 remains at
2027-09-26 23:30. Mirassol–Vasco remains unplayed.

## Verified Task 04B acceptance and ordinary merge

PR #8 head `315056f3f22325732012bf60c71f6f36b62a4d6e` passed
[CI 40631761863](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40631761863):
287 tests on each Windows/Linux Python 3.11–3.13 job, unchanged engine/world golden
hashes and an independently restored season archive.

The human stored a repository-scoped fine-grained PAT via the hidden Windows
Credential Manager prompt. Earlier tokens authenticated but could not see the
private repository; the replacement verified pinned repository ID `1436541980`,
worker/user ID `78325376`, issue/comment and GraphQL edit-metadata access. No
credential was printed, logged or put in configuration. Persistent operation uses
that scoped PAT, not the earlier development OAuth login.

The frozen 0.8.0 wheel was independently installed at `output/task04b-runtime`.
Normal iPhone ChatGPT created [private issue #6](https://github.com/Lbragaa/BragaEraCommandBridge/issues/6),
UUID `9d6b2f84-3f45-4d90-a6c8-75b9e1240e63`, sequence 4. The persistent worker
posted [comment 6480460530](https://github.com/Lbragaa/BragaEraCommandBridge/issues/6#issuecomment-6480460530)
and closed the issue roughly 29 seconds after creation. Local verification checked
the exact HMAC-sealed ledger/comment match: only event 13, SECOND_HALF_KICKOFF,
no postmatch data, next sequence 5. The human then confirmed that normal phone
ChatGPT retrieved that actual comment and narrated only its returned event.

The explicitly opted-in login task `BragaEraBridge-1436541980` verified enabled
login trigger/type 9, least privilege/run level 0, no password and IgnoreNew
instance policy. A controlled task-driven process restart succeeded. Reopening
unchanged issue #6 retained one comment, one delivered event and sequence 5. The
two Python processes are a venv launcher/child, not competing workers. Physical
sleep/wake/reboot/login was not tested and is not inferred from manual task launch.

After this real mobile send/receive proof and a repeated green-head check, PR #8
was ordinarily merged as **`51f3223b9d0bc0175b23e7630330bcdc439d352b`**, parents
`05267a6ae8cab8ed27803b6e052ecf7b34ba38f5` and `315056f…`. Post-merge main CI:
[40768031023](https://github.com/Lbragaa/FootballSimulatorStuff/actions/runs/40768031023).
Its final status must be recorded before readiness. One Task 04C branch is used:
`codex/task-04c-phone-operations`. No history was rewritten.

## Implemented versioned extension

Package 0.9.0 adds opt-in braga-bridge-2 / bridge-control-2 over existing lineage
profile 2. Engine/world/payroll/save behavior is unchanged. V1 grammar, cached
replies and sealed inbox storage remain compatible.

- Closed v2 schemas and a separate control scope. Issues prepare/review; generic
  execute/accept/provision/code/path commands remain absent. Read/narration does
  not inherit missing control privileges.
- Exact prepare, authorize, execute, independently verify and accept stages using
  the existing lineage signatures, claims and immutable commitments. Each
  irreversible stage requires its own human challenge. Executing alone does not
  accept a successor.
- Direct pinned-human, unedited GitHub confirmation with a separately enrolled
  authenticator. ChatGPT-created issues/general chat are not separate consent.
  One active challenge prevents redirection of a visible TOTP to another action.
  Codes/comments cannot approve twice; expiry, rate limits and sealed mode/key/
  identity context fail closed.
- Durable human proof before effects, plus authenticated control receipt outbox.
  Crashes resume the same proof, seed, execution directory and candidate. Invalid
  validation retains the operation rather than releasing claims. Extreme GitHub
  visibility delays may duplicate identical physical comments; clients deduplicate
  receipts while state effects remain once-only.
- Earliest-group roundups use existing signed pages only, hold selected detail,
  protect Vasco (club 15) and never simulate or jump to future kickoffs.
- Lossless compact event presentation deduplicates identical on-field identity
  arrays by SHA256; previews retain ID/name maps and old signed events stay intact.
- Interactive TEST-only setup/enrollment. It cannot provision/enroll production.
  Production needs an existing trusted active authority, separate signed local
  policy/control receipt, authenticator and explicit binding. Provisional model
  approval does not create them or authorize a match.

GitHub account authentication is the remote transport boundary. TOTP provides
separate human possession; compromise of the trusted runtime/local keys remains
outside that protection. Normal ChatGPT checks GitHub author/bindings, not HMAC
mathematics. It must never receive signing, PAT or enrollment secrets.

## Local verification and noncanonical rehearsal

The initial focused suite passed 72 cases; v2 protocol, delivery and enrollment
coverage expanded it. The full suite now contains **328 tests** and is running,
not yet claimed passing. Existing tests remain. New cases cover malformed/unknown
commands, identity/scope, edited/App/incorrect approvals, replay/expiry/rate limits,
single-action fencing, crashes before/after effects/posts, invalid-comment
reconciliation, missing-journal refusal and compact identity reconstruction.
A Windows handle test found an unclosed SQLite initializer; explicit closing now
follows commit, without changing journal contents or football behavior.

The 0.9.0 wheel was installed separately at `output/task04c-runtime` and imported
outside the checkout. Final commit/wheel/CI references must be recorded before
acceptance; a local wheel is not proof of full phone operation.

`output/task04c-controller-rehearsal/rehearsal.json` records a fresh TEST authority,
fixed seed `task04c-control-rehearsal-fixed-v1`, public dummy credentials and
**simulated** approvals. Manifest:
`26f8945f64867cda0effd0e5f9912baf5b70946e8a7cf253fcc81fb849f59553`.
It completed 16 continental fixtures/payroll once, post-archive crash recovery,
independent replay/restoration, separate acceptance and post-accept-commit receipt
recovery. Exactly one TEST successor, 16 execution receipts, one paid obligation
and 16 reveal cursors were verified. A roundup delivered 15 games while one stayed
for detail; duplicates/new Career objects resumed the same signed page/head.

The first delivery attempt caught an incorrect guard constant (club 5 is
Fluminense, Vasco is club 15). After fixing and testing against accepted identities,
the SAME already accepted TEST successor resumed; no replacement seed was chosen.
This local test is not real GitHub/phone consent or physical reboot evidence.

## Live v2 rehearsal and remaining gates

A separate fresh `output/task04c-phone-test` namespace is prepared from exact 046C:
TEST-only career `task04c-phone-test-v1`, fixed seed `task04c-phone-rehearsal-fixed-v1`.
The earlier Task 04B ledger/cursor stays intact. This is a required from-root
control rehearsal, not a reset of that prior career. No batch in the new career
has been authorized/executed. The human successfully enrolled its authenticator
in their interactive local console. Strict verification confirmed the enrolled
gate and signed TEST-only policy; no enrollment secret/code was displayed here.
The frozen v2 worker passed scoped polling and replaced the earlier TEST startup
task using the already explicit opt-in. Status #1 now advertises protocol 2,
this new career, root hash, sequence 1 and TEST-only control capability. Both
production-binding flags remain false; no irreversible action has occurred.

Remaining: exercise normal phone inspection/preview, separate exact human authorization,
execution/verification/acceptance, narration/roundup and new-conversation resume;
record actual issue/comment/receipt references; complete full regression/main/PR
CI; leave the Task 04C PR open. Unperformed physical login/sleep tests remain
explicit limitations, not invented evidence.

All six protected original/046C/archive/approval/registry hashes were checked
unchanged after the rehearsal. Vasco–Palmeiras remains final. Mirassol–Vasco is
scheduled in the accepted root and September 30 TEST successor. No future Vasco
result is revealed in ordinary summaries.

## Production readiness

Read [protocol 2](bridge_protocol_v2.md), [Hikari procedure](bridge_hikari_v2.md)
and [local setup/production checklist](phone_official_operations.md). Ordinary
play needs the PC online and worker running; irreversible stages add a direct
GitHub-mobile/authenticator confirmation. There is no routine PC/Codex/API/file
handoff after setup. A GitHub connector itself is not a Python runtime.

**Do not yet declare full phone-only official gameplay ready.** V2 human-confirmed
phone rehearsal and final verification remain. Actual production key/authority/
seed, signed policy receipt, enrollment/binding and first batch decisions remain
separate future human actions. No paid cloud, dashboard, transfer market or 2028
expansion is introduced.
