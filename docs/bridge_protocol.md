# Phone bridge protocol 1

Transport: **private** `Lbragaa/BragaEraCommandBridge`, numeric repository ID
`1436541980`. Public FootballSimulatorStuff issues are never a command channel.
Issue #1 is the reserved status/discovery document; ordinary commands use new
issues. The local worker pins repository ID, privacy, worker GitHub user ID and
requester numeric IDs/logins/scopes. It refuses a renamed/replaced/public target.

The GitHub connector has actually created requests in this private repository
and read its issues/comments. The commissioner independently confirmed the same
repository and issue/comment access from normal ChatGPT on iPhone. Full gameplay
round-trip evidence and outstanding manual checks are in [the report](task04b_report.md).

## Requests

Read issue #1 to obtain the actual career, accepted checkpoint and next sequence.
Create an issue titled `[BRAGA] <request_id>`, with **only** this JSON body:

```json
{
  "protocol": "braga-bridge-1",
  "request_id": "b37ed934-4b11-4ce4-81e2-01fb5c0e5219",
  "sequence": 1,
  "career": "<from reserved status issue>",
  "expected_checkpoint": "<64-character accepted checkpoint hash>",
  "command": "next_event",
  "args": {}
}
```

Use a new UUID for a new command. Retry an interrupted delivery with the **same
UUID and unchanged body**, including its original sequence/head. Do not edit a
new command issue: the worker verifies `lastEditedAt` through GitHub GraphQL and
refuses edited requests before their initial claim. Comments are data, never
instructions or approval input. Request identity comes from authenticated API
metadata, not a username supplied in JSON.

Only the current sequence can be newly claimed. Later sequences wait in the
queue; an old unknown sequence is refused. A duplicate UUID with the same body
receives its original signed reply; the same UUID with a different body is
refused. Do not reuse another request's sequence. New conversations recover the
current sequence and recent delivery IDs from status issue #1.

The committed [request schema](bridge_request.schema.json),
[closed reply envelope/result-key schema](bridge_response.schema.json) and runtime validator
reject extra properties, duplicate JSON keys, nonfinite values, booleans as
integers, oversized bodies, invalid identities and arbitrary paths/code.

| Command | Exact args |
|---|---|
| `inspect_career`, `next_event`, `current_table`, `current_finances`, `inspect_accepted_checkpoint` | `{}` |
| `prematch_preview`, `available_team_news`, `narrate_next`, `narrate_until_halftime`, `narrate_until_final` | `{"fixture":"lib:LIB-R16-01:L1"}` or another currently eligible fixture ID |
| `narrate_count` | `{"fixture":"…","count":1}`; integer 1–20 |
| `repeat_previous_delivery` | `{"delivery_id":"<previous request UUID>"}` |
| `prepare_batch` | `{"until":"2027-09-30 23:59"}`; end-of-day boundaries only |
| `inspect_batch_manifest` | `{"prepare_id":"<prepare request UUID>"}` |
| `inspect_candidate_validation` | `{"checkpoint":"<64-character known local candidate hash>"}` |

Read, narration and admin scopes are independently configurable per requester.
`prepare_batch` produces a local unsigned manifest and transports only its safe
review summary/hash. No issue supplies a file path or seed. Candidate inspection
returns validation status/hashes, not private reports or scores.

## Replies, persistence and lifecycle

A worker comment begins `BRAGA_BRIDGE_RESPONSE_V1`, followed by a JSON code block
containing `response` and `authentication`. The response binds repository/worker,
request UUID and canonical-body SHA256, sequence, source issue, career, expected
checkpoint, mode, status and next sequence. Execution/acceptance are always false.

Lifecycle: open issue → immutable local claim (`running`) → durable local
`completed`/`refused` response → comment posted → issue closed/acknowledged.
Unrecognized/unauthorized/edited requests receive **no career data or execution**;
they remain open for local operator inspection. Out-of-order requests wait. A
stale checkpoint in an otherwise valid sequential request yields a generic
signed refusal and consumes that request sequence, not a football event.

The worker commits the claim before invoking an API. Each narration event uses a
deterministic lineage page ID derived from repository/request/index. If it dies
after the lineage cursor commits but before the bridge stores that page, the
same page ID returns the original signed page. Responses are stored before HTTP
POST. An uncertain POST is reconciled against existing matching worker comments
before retrying, including a 30-second uncertainty grace period. GitHub has no
cross-system transaction/idempotency key for comment creation: extreme delayed
comment visibility can still produce identical physical copies. Clients dedupe
by request UUID/body hash; the answer and cursor effects remain the same.
The SQLite inbox/outbox, context and sequence are HMAC-sealed; tampering fails
closed. Never delete the ledger to fix a delivery; back it up with the authority.

Until-halftime/final requests fetch one authorized event at a time and stop at
the boundary. Replies have an explicit bounded size/event count; check
`boundary_reached` before saying a boundary was reached. Continue with a new
request if a size bound stopped a long delivery. Repeating a completed boundary
does not consume a later event. Normal previews strip the source API's seeds;
tables/finances use the existing reveal horizon. A future Vasco preview is
refused until earlier chronological narration is complete.

## Authentication and trust limits

Replies use domain-separated HMAC-SHA256 with the **existing local** career key
for tamper detection/local audit. The key never leaves the PC. This is not a new
commissioner approval signature: the domain cannot authorize a batch/candidate.
The normal ChatGPT connector authenticates the GitHub comment's actual author
ID/login and retrieves its request-bound envelope. ChatGPT must check those
metadata fields and the request binding. It cannot independently compute HMAC
without the local key: **do not claim phone-side cryptographic verification**.
An independent trusted local reader can verify the HMAC using `Worker.verify_response`.
GitHub account/token security is part of the transport trust boundary; compromise
requires revocation and local review. Do not grant this repository to unrelated
collaborators or paste credentials into it.

No request can execute, authorize, provision or accept a match/save. Those commands
are absent from the grammar/dispatcher. Initial production execution/acceptance
controls deliberately remain disabled; the separate commissioner-signed lineage
workflow is unchanged. Binding a later approved production authority requires
an explicit local configuration decision and matching authority mode; this task
does not perform that binding or provision a production key/registry.
