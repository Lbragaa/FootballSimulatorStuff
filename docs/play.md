# Play THE BRAGA ERA from ChatGPT

The PC must be online, and its Windows worker starts at login. Codex may be
closed. Use normal iPhone ChatGPT with the GitHub connection enabled for private
`Lbragaa/BragaEraCommandBridge`. No routine terminal, files, GitHub-mobile
confirmations or authenticator codes are needed.

First activation, once for the official career:

> Hikari, enable automatic gameplay for THE BRAGA ERA and continue.

Afterward:

> Hikari, continue THE BRAGA ERA.

Ask for pregame/lineups/tactics, standings/finances, halftime/full-time narration,
or summaries of other games. Choose a particular game for detailed coverage if
wanted. Hikari must use actual worker outputs only, with no invented outcomes.

## Hikari client instructions

1. Read private status issue #1: current career, protocol, checkpoint and next
   sequence. Never assume a prior conversation's sequence/head is current.
2. Use the existing strict JSON envelope and a fresh UUID for each new command:
   `protocol`, `request_id`, `sequence`, `career`, `expected_checkpoint`, `command`,
   `args`. Title `[BRAGA] <UUID>`. Do not edit the issue body after creation.
   Within the same turn, use the last matching reply's `next_sequence`; status #1
   can briefly lag comment delivery. After an advance, use the reply's returned
   `accepted_checkpoint` as the next parent. Never reuse an older status value.
3. On the user's explicit first opt-in, send `enable_automatic_gameplay` with
   `{"confirmation":"ENABLE_AUTOMATIC_GAMEPLAY"}`. This binds standing authority
   to the advertised career. Do not enable it merely because software is ready.
4. For “continue”, send `continue_gameplay` with `{}`. It narrates stored events
   first. If none wait and mode is enabled, it advances one chronological batch
   and returns a spoiler-safe pregame view. A single call never simulates another
   batch while narration is available. Tell the user when simulation advanced.
5. Default detailed coverage to Vasco; offer/use concise engine-backed `roundup`
   results for unrelated eligible fixtures, respecting any user-selected detail.
   Do not simulate another batch in the same user turn just to skip to Vasco.
   Earlier scheduled commitments must be completed in order.
6. Existing `prematch_preview`, `available_team_news`, `current_table`,
   `current_finances`, `narrate_next`, `narrate_count`, `narrate_until_halftime`,
   `narrate_until_final` and `roundup` remain available. Never reveal events or
   postmatch statistics before their authorized page/final whistle. Continue a
   bounded narration delivery with a new sequence until its requested boundary.
7. `advance_next_batch` is an explicit advance command with `{}`; it returns
   `narration_ready` without new simulation if unrevealed results remain.
   `automatic_status` inspects mode; `disable_automatic_gameplay` restores the
   requirement for manual approval of future batches. Disabling does not erase
   already committed operations or change any result.
8. Fetch comments directly. Accept only matching `BRAGA_BRIDGE_RESPONSE_V1`
   envelopes from actual worker user ID `78325376` / login `Lbragaa`, pinned
   private repository ID `1436541980`. Check UUID, career, sequence, parent/head,
   mode and status. HMAC is local audit integrity, not independently verified
   phone cryptography. Never request its key or any PAT.
9. If offline or interrupted, keep the SAME issue/UUID. Retry/read its original
   reply instead of creating replacement simulations. A new conversation reads
   #1/recent delivery comments and resumes the same cursor and career.

The existing accepted root is always immutable. Automatic gameplay uses signed
career delegation and existing exact manifests, precommitted seeds, independent
checkpoint replay/restoration and atomic acceptance. It deliberately trades away
separate per-batch human approvals for personal-game convenience. Merely starting
the worker never executes football; a recognized user command is required.
