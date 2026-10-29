# THE BRAGA ERA — Hikari career episodes

Use normal iPhone ChatGPT with GitHub connected to this PRIVATE repository.
The existing Windows Python worker is the football/state authority. The PC must
be online; Codex can be closed. No routine codes, hashes, files or terminal.

Say **“Hikari, continue THE BRAGA ERA.”**

Hikari: read the current procedure at
https://github.com/Lbragaa/FootballSimulatorStuff/blob/codex/career-episodes/docs/play.md
(also available on main after ordinary review/merge).

1. Read status issue #1 for the CURRENT career, checkpoint, protocol,
   next_sequence, automatic_gameplay and recent requests. Never hardcode an old
   save/head/date/sequence. Official play is already active: do not re-enable it
   or create another career merely because this is a new conversation.
2. If a recent request is running, read THAT issue's comments and wait. Do not
   issue a replacement. After interruption/new conversation, resume that request.
3. For ordinary continue, create ONE issue `[BRAGA] <fresh lowercase UUID>` with
   this plain JSON envelope (substitute current fields, no Markdown fence):

```json
{"protocol":"braga-bridge-2","request_id":"<same UUID>","sequence":123,"career":"<from status>","expected_checkpoint":"<from status>","command":"play_next_episode","args":{}}
```

Do not edit an issue body. Retry/read the SAME issue/UUID, never replace a pending
simulation. Use the matching response's next_sequence and accepted_checkpoint
within a turn; status can briefly lag comment delivery. Wait for one final reply.

An episode handles earlier world games/payroll internally, then returns Vasco's
complete match and completed rodada, a significant completed cup stage or an
explicit blocker/progress bound. Do not create separate date, kickoff, roundup,
halftime or final-whistle requests for ordinary play. Several minutes of verified
local processing can be normal. Merely starting the worker executes nothing.

**Presentation is an ordered ARRAY. Render its sections IN ORDER:**
prematch/actual autonomous lineups → chronological events through final whistle
→ final score/statistics/brief manager assessment → complete league table → next
fixture. Narrate each goal BEFORE saying the score including it. No spoiler in
the opening headline, winner, summary, preview or later-goal hint. Halftime is
inside the complete commentary, not another approval/command. Luan Braga remains
an autonomous manager, not the human's playable avatar. No invented quotes.

Ordinary unrelated scores remain silent. A milestone report consolidates actual
tie results, aggregates/penalties, qualifiers and established draws. Never invent
a draw, winner or early continental place. `round_pending` is explicitly partial;
do not call its table final. `progress_bound` permits a subsequent ordinary
continue from durable progress. A retry of the old UUID returns its old delivery.

Read comments DIRECTLY. Accept only matching BRAGA_BRIDGE_RESPONSE_V1 envelopes
from worker ID 78325376/login Lbragaa in private repository ID 1436541980. Check
UUID, sequence, career/head, mode and status. HMAC protects LOCAL audit integrity;
do not pretend to verify it independently on the phone or request its key/PAT.

`disable_automatic_gameplay` stops future automatic advancement. Existing
committed work retains its seed/results. `automatic_status` inspects mode.
`enable_automatic_gameplay` still requires explicit human career-specific opt-in
with {"confirmation":"ENABLE_AUTOMATIC_GAMEPLAY"}; do not infer consent.

Legacy inspections, detailed narration, roundups, manual approvals and single-day
commands remain available on explicit request. Never use legacy continue_gameplay
as the default episode command. Existing ledger/issues/receipts are not reset.

Never upload keys, credentials, databases, archives, authorization files or private
future diagnostic reports. No Codex/OpenAI API, Actions gameplay runner, dashboard
or paid service is required. An offline PC queues the same request safely.
