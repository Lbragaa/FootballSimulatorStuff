# Private phone bridge protocol 2

`braga-bridge-2` is an opt-in communication extension, not a football engine or
checkpoint profile. Runtime 0.9.0 uses the existing lineage profile 2. GitHub
repository `Lbragaa/BragaEraCommandBridge` must remain private, ID `1436541980`.
Worker and authorized human IDs are pinned locally. No OpenAI/Codex API or
GitHub Actions gameplay runner participates in polling or execution.

The envelope retains the [v1 fields](bridge_protocol.md): `protocol`, UUID
`request_id`, integer `sequence`, `career`, exact `expected_checkpoint`, `command`
and closed `args`. Create `[BRAGA] <UUID>` issues with plain JSON bodies; do not
edit them. Discover current career/head/sequence from issue #1. Historical v1
requests/replies remain supported with their original grammar and bytes. An
upgrade of the same career uses the original sealed inbox, never a reset.

V2 also supports every v1 read/narration/admin command. Additional commands:

| Command | Exact args | Scope | Effect |
| --- | --- | --- | --- |
| `prepare_control_batch` | `until` (`2027-MM-DD 23:59`) | control | Persist unsigned exact manifest locally; return review and `preparation_id` |
| `inspect_control_batch` | `preparation_id` | control | Return inventory, commitments, versions and batch state |
| `request_authorize_batch` | `preparation_id`, `manifest_sha256` | control | Return exact authorization challenge; no authority yet |
| `request_execute_batch` | `preparation_id`, `manifest_sha256` | control | Require prior signed authority; return distinct execution challenge |
| `inspect_control_candidate` | `preparation_id` | control | Independently validate and return only candidate/archive hashes |
| `request_accept_candidate` | `preparation_id`, `checkpoint_sha256` | control | Return a separate exact validated-successor challenge |
| `roundup` | `fixtures`, `detailed` (unique disjoint fixture arrays, at most 16 each) | narration | Reveal only selected eligible stored results; hold detailed matches |

Hashes are 64 lowercase hex characters; preparation IDs are canonical UUIDs.
The runtime additionally enforces array disjointness, real chronology and
eligibility. Raw code, paths, secret/code fields and generic approve/execute/
accept/provision commands are rejected. Request size is bounded to 8 KiB.
See [request schema](bridge_request_v2.schema.json) and
[response schema](bridge_response_v2.schema.json). Sealed local journal storage
retains format 1; the transport version is not permission to rewrite that journal.

## A challenge acknowledgement is not an executed operation

Normal request replies retain `BRAGA_BRIDGE_RESPONSE_V1` and the signed
`bridge-delivery-1` envelope, with `response.protocol=braga-bridge-2`.
Closing an issue acknowledges delivery of its response. A control-request reply
with `result.confirmation.state=awaiting_human` means only that a challenge is
ready. It does not authorize, execute or accept anything.

The human must review the exact action/manifest/candidate, then post the returned
confirmation format **directly in GitHub mobile/browser**, replacing only the
placeholder with the code from the separately enrolled Braga authenticator:

```text
BRAGA_CONFIRM_V1 <challenge UUID> <binding SHA256> <six-digit code>
```

The comment can be on the now-closed command issue. Do not put codes in command
issues or send authenticator secrets/PATs/authority keys through ChatGPT. Only
one active challenge is allowed; a consumed authenticator counter cannot approve
another action. GitHub App comments, changed identities, edited confirmations,
wrong bindings, stale parents, expired challenges and replayed codes fail closed.
See [the consent/trust model](phone_official_operations.md).

After a valid separate human comment, the worker posts
`BRAGA_CONTROL_RECEIPT_V2` followed by a JSON `{document,signature}` envelope.
Its document binds domain `bridge-control-receipt-2`, protocol, repository and
worker IDs, career/mode, challenge/issue, action, target/manifest/parent hashes,
local human-proof hash and the minimal completed result. The human proof is
durable before effect. The receipt is posted after the original lineage API
transaction/independent validation, never from a predicted outcome.

Validate actual GitHub author metadata and all bindings. HMAC provides local
audit integrity, not independent phone-side signature verification. A normal
ChatGPT client must not ask for the key or claim it verified the HMAC itself.
An invalid-confirmation notice is not a completed control receipt.

Authorization, execution and acceptance each require a different challenge and
human decision. Software approval or policy approval alone authorizes no match.
After execution, the accepted head remains the parent until separate acceptance.
Expect the accepted head to change only after a successful acceptance receipt.
Execution/acceptance capability flags mean approved controls are available;
they never mean a particular batch/candidate is already authorized.

## Spoiler-safe delivery and resumption

All result-producing operations use existing lineage authority and exact claims.
No GitHub message can overwrite SQLite directly. Pending committed operations
resume their original signatures, execution ID, seed commitments and output
directory. A failed validation retains the operation for review; it does not
release claims or search for a new seed.

Control receipt posting has a sealed local outbox and reconciliation grace
period. As with v1, GitHub cannot guarantee one physical comment under extreme
delayed visibility; identical receipts are deduplicated by challenge ID and body
hash. State effects remain once-only. Do not create replacement requests when
the worker is offline or a reply is delayed.

V2 narration adds `presentation=bridge-events-2`, `on_field_states` and original
`source_page_sha256s`. Event on-field arrays are replaced by
`on_field_state_sha256` references. The referenced home/away ID arrays are sent
once per distinct state in a delivery; verify their SHA256 and reconstruct them
when precise identity is needed. Other event data and ordering remain intact.
Pregame previews retain ID/name mappings. Earlier signed pages are never changed.

A roundup consumes stored signed pages through each selected final whistle,
then releases those finals only. It does not simulate. Choose detailed fixtures
first; they stay pending and prevent a jump past their kickoff. Vasco (accepted
club ID 15) always stays out of automatic roundups. “Toward Vasco” still requires
all earlier commitments and separate authority for any unexecuted batch.

## Read privileges and local setup

Read/narration scopes are independent of `control`. Missing policy receipt,
authenticator enrollment or production-control binding disables control requests
while leaving legitimate read/narration available. A missing trusted career
authority or wrong career/mode still rejects the whole connection.

The [TEST setup helper](phone_official_operations.md) supports only a NEW TEST
career and interactive TEST authenticator enrollment. It cannot provision or
enroll production authority. Production needs separately approved existing local
authority/key/policy receipt and explicit production binding. No production setup
or official execution is performed by Task 04C.
