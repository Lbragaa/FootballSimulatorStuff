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
→ final score/statistics/brief manager assessment → round/other results → complete league table → next
fixture. Narrate each goal BEFORE saying the score including it. No spoiler in
the opening headline, winner, summary, preview or later-goal hint. Halftime is
inside the complete commentary, not another approval/command. Luan Braga remains
an autonomous manager, not the human's playable avatar. No invented quotes.

Show `episode_results`: all ten rodada scores, completed relevant other games,
each recorded cup leg, aggregates/penalties and confirmed qualifiers. Do not
repeat the full Vasco commentary. `exhaustive=false` explicitly means some
results/ties exceeded the comment-size allowance: state omissions and offer the
provided historical retrieval page, never pretend the report was exhaustive.
A milestone report consolidates actual
tie results, aggregates/penalties, qualifiers and established draws. Never invent
a draw, winner or early continental place. `round_pending` is explicitly partial;
do not call its table final. `progress_bound` permits a subsequent ordinary
continue from durable progress. A retry of the old UUID returns its old delivery.

## Historical scores — read-only, available at any later career point

Use command `historical_results` with optional args: competition (human name),
season (integer), round (integer), stage (QF/SF/FINAL/R16/R32/PO/GROUP or its
Portuguese/English name), leg (1/2), club (recorded name), date OR date_from/date_to
(YYYY-MM-DD), recent (1–500), limit (1–50, default 20), include_pending (boolean),
or the opaque continuation cursor. No fixture key is needed.

Examples:
```json
{"competition":"Brasileirão","season":2027,"round":29,"limit":50}
{"competition":"Libertadores","season":2027,"stage":"QF","leg":1,"date_from":"2027-10-01","date_to":"2027-10-31"}
{"competition":"Copa do Brasil","season":2027,"stage":"QF","limit":50}
{"club":"Vasco","season":2027,"recent":10}
{"date_from":"2027-10-01","date_to":"2027-10-31","limit":50}
```

Use the SAME normal protocol envelope, replacing command/args. An empty {} gives
coverage plus an initial page. Read result.historical_results, including matches,
ties, score availability, selection completeness and limitations. For every
has_more=true page, request {"cursor":"<unchanged next_cursor>"} in a fresh
normal UUID/sequence until false. Do not silently truncate a season at 20/50
games. The cursor pins reporting data; use the reply's OUTER accepted_checkpoint
for the next command head. Date filters exclude genuinely undated old fixtures.

This does not simulate, advance time, consume commentary or change any cursor.
It works even with automatic gameplay disabled. First-leg results are available
as soon as accepted; no need to wait for the entire stage. Unknown historical
scores/resolutions remain unknown. Unfinished Vasco narration still withholds
its final score/tie outcome. Report structured errors honestly. Use only actual
accepted records; never reconstruct a score from standings, prose or a guessed
aggregate. Refer to docs/historical_results.md in the engine repository for
source coverage, pagination and legacy limitations.

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
