# Task 04B — private phone gameplay bridge

**TEST-ONLY integration. Production execution/acceptance disabled.** This report
distinguishes implemented/tested behavior from the human setup/mobile checks
still pending. No official fixture, Save 047, production authority, key relocation
or official fictional-time advance is performed.

## Implementation

The single working branch is `codex/task-04b-phone-bridge`, based on main
`05267a6ae8cab8ed27803b6e052ecf7b34ba38f5`. Package 0.8.0 adds a standard-library
worker, not a new football engine. Existing 1.0/1.1 configurations, world 2.1,
knockout 2.1 and lineage profile 2 remain unchanged.

Private transport: [Lbragaa/BragaEraCommandBridge](https://github.com/Lbragaa/BragaEraCommandBridge),
repository ID `1436541980`; worker/commissioner user ID `78325376`/`Lbragaa`.
Issue #1 publishes signed status and sequence discovery. The processor handles
the 15 requested inspection/narration/review commands through existing APIs,
with a closed request grammar, per-user scopes and checkpoint binding.

The worker is ordinary Python + GitHub HTTPS. It has no Codex/OpenAI API, model
SDK, Actions runner, dashboard or inbound HTTP endpoint. A local SQLite queue
records requests/pages/responses before delivery; the old signed lineage page
IDs/cursors remain authoritative. Network uncertainty and worker restart resume
the same page/response. Duplicate UUIDs never consume more events. Same UUID with
different contents, invalid roles/identities/paths, edited new issues, wrong heads
and public/replaced repositories fail closed.

The underlying preview API includes seed commitments. The bridge explicitly
filters them and screens public results for private fields. Only chronological
pages and reveal-horizon tables/finances are posted. Preparation returns an
unsigned review summary/hash, not authorization files. Unknown team news before
an accepted forward snapshot stays explicitly unknown.

## Connector and live test evidence

- The installed GitHub connector created the private probe issue #1 and fetched
  its comments. The human independently confirmed those operations from a normal
  ChatGPT conversation on iPhone; this was **read access**, not yet mobile creation.
- [Issue #2](https://github.com/Lbragaa/BragaEraCommandBridge/issues/2): the connector
  created `next_event`, the initially offline local worker later read it, and the
  connector retrieved the signed engine-backed comment. The issue was acknowledged
  and closed. It returned the 16 pending continental narration fixtures, no scores.
- [Issue #3](https://github.com/Lbragaa/BragaEraCommandBridge/issues/3): the same path
  returned a filtered Bolivar–Palmeiras pregame preview with no seeds/postmatch data.
- [Issue #4](https://github.com/Lbragaa/BragaEraCommandBridge/issues/4): the worker
  delivered 11 pages, event sequences 2–12, stopping exactly at `HALF_TIME`;
  `postmatch_available=false`. Event 1 was already narrated in the reused portable
  TEST fixture, not silently lost by the bridge.
- [Issue #5](https://github.com/Lbragaa/BragaEraCommandBridge/issues/5): a second
  issue using the exact same UUID/body returned the byte-equivalent signed
  halftime envelope. Sequence discovery stayed at 4 and no further event was
  consumed. Separate worker Python processes were used between polls.

These development one-shot polls reused the existing GitHub login **only in
memory**. Its token was never printed, saved or put in an issue. The persistent
CLI rejects that broad credential and requires the separately configured,
fine-grained repository-scoped PAT in Windows Credential Manager. The disposable
career is a restored copy of the old public-key TEST rehearsal, not an official
authority or an operational production transfer. Accepted package bytes remain
immutable; only the isolated authority/session cursors are changed.

## Tests and remaining acceptance gates

The focused bridge suite passed **49 tests**: closed schemas, duplicate JSON,
invalid users/roles, edited requests, sequence collisions, wrong heads, future
preview denial, same-ID delivery, halfway/final boundaries, offline queue,
uncertain HTTP POST, crash at three delivery stages, process-object restart,
sealed-ledger tampering, pinned transport/mode, secret-field filtering and real
signed-page retry/reveal behavior on an isolated existing career. No new football
match is generated for these focused tests. Extra cases cover a crash on the
first boundary page, retention/recovery of a partially delivered request and the
pre-POST reconciliation grace period. Full regressions/CI are recorded in
the implementation PR when complete; pending runs are not claimed as passing.

Outstanding human checks at this report's preparation:

1. Store the fine-grained PAT using the hidden local `credential-set` prompt.
   Do not send the token through ChatGPT. Until this is complete, no unattended
   production-like worker is configured; the development one-shot is not a
   substitute for it.
2. From **normal iPhone ChatGPT**, create a real continuation request (sequence 4
   after the demonstrated halftime) and retrieve its worker response. An async
   request for this test has been presented to the commissioner.
3. Once the scoped test worker runs, verify a new phone conversation resumes the
   same cursor. Unit/restart tests and the connector round trip do not by
   themselves prove the complete phone UX.
4. Explicitly choose whether to enable login startup. Actual Windows sleep/wake
   and physical reboot/login testing remain human checks; no disruptive sleep or
   reboot is initiated here. The setup tool is opt-in, least privilege, no Windows
   password, and does not prevent sleep.

**Do not declare the full phone-first success criterion met while these required
live checks remain pending.** Report a precise credential/client/startup blocker
instead of inventing an engine reply or routing ordinary play through Codex.

## Security and operations

GitHub authenticated identity/permissions plus the pinned private repository are
the phone transport's trust boundary. HMAC authenticates stored responses for
local audit; normal ChatGPT cannot independently calculate it without the key.
Do not claim phone-side cryptographic verification. No key is sent to the phone.
The GitHub account/PAT must remain secure; compromise requires revocation and
local review. Future production binding is explicit and must match an already
approved local authority. This task does not create that authority or perform
the binding. Execution/acceptance commands remain disabled even on a future
production connection until a separately tested authorization workflow exists.

See [protocol/request schema](bridge_protocol.md),
[Windows credential/startup setup](bridge_windows.md),
[Hikari mobile instructions](bridge_hikari.md) and
[response schema](bridge_response.schema.json).

The transport-independent processor can later use a supervised Linux process and
a secret-manager environment credential. No paid cloud service is deployed; no
official key is moved. A sleeping/off PC cannot answer until it resumes. Changing
ChatGPT conversations does not reset the PC's authority, ledger or cursor.
