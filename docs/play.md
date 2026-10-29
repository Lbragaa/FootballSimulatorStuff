# Play THE BRAGA ERA from ChatGPT

The PC must be online, and its Windows worker starts at login. Codex may be
closed. Use normal iPhone ChatGPT with the GitHub connection enabled for private
`Lbragaa/BragaEraCommandBridge`. No routine terminal, files, GitHub-mobile
confirmations or authenticator codes are needed.

First activation, once for the official career:

> Hikari, enable automatic gameplay for THE BRAGA ERA and continue.

Afterward:

> Hikari, continue THE BRAGA ERA.

Ordinary continuation now returns one complete **career episode**, usually
Vasco's next match through the final whistle, the completed rodada table and next
fixture. Earlier unrelated games and payroll are handled internally. A completed
cup stage or genuine dependency can instead be the episode's stopping point.
Luan Braga remains an autonomous manager; the commissioner is not his avatar.
Hikari must use actual worker outputs only, with no invented outcomes.

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
4. For “continue”, send **`play_next_episode` with `{}`**, ONE issue. Wait for its
   single matching response; do not crawl through dates, roundups or halftime
   using additional issues. The worker resumes stored narration first, consumes
   unrelated fixtures internally, and uses individually verified next-day
   batches until Vasco's match/rodada, a major milestone, or a real blocker.
5. Render `presentation` **in array order**, even if a JSON viewer alphabetizes
   object keys: prematch/recorded lineups → chronological timeline → final
   whistle → fulltime/statistics/brief assessment → completed table → next
   fixture. Narrate each goal BEFORE saying its updated score. No opening
   full-time headline, winner, recap, statistics or later-goal hints. Halftime is
   part of the same commentary. Resume interrupted timelines at their first
   returned event. Default other games to silence, not individual score lists.
   A `milestone_report` consolidates actual ties, aggregates, penalties,
   qualifiers and established draws; never invent pairings or early continental
   berths. `round_pending` explicitly means no final rodada table is available.
6. Existing `prematch_preview`, `available_team_news`, `current_table`,
   `current_finances`, `narrate_next`, `narrate_count`, `narrate_until_halftime`,
   `narrate_until_final` and `roundup` remain available. Never reveal events or
   postmatch statistics before their authorized page/final whistle. Continue a
   bounded explicit narration delivery with a new sequence until its requested
   boundary. Legacy `continue_gameplay` keeps its original single-page/day flow.
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

An episode is bounded to 35 calendar days, 16 verified batches, 120 revealed
fixtures, 256 signed pages, a 30 KB running presentation and 15 minutes between
atomic operations. A running atomic operation finishes safely before a time
bound takes effect. `progress_bound` returns durable partial progress rather than
skipping anything. One subsequent ordinary continue resumes it; retrying the old
UUID returns its exact original delivery. The signed comment stays below 60 KB.
The PC may take several minutes to simulate and independently replay a busy
episode. Do not submit a second command while the first request is running.

The existing accepted root is always immutable. Automatic gameplay uses signed
career delegation and existing exact manifests, precommitted seeds, independent
checkpoint replay/restoration and atomic acceptance. It deliberately trades away
separate per-batch human approvals for personal-game convenience. Merely starting
the worker never executes football; a recognized user command is required.
