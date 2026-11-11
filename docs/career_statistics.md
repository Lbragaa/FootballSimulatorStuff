# Career statistics

Use a single protocol-2 read command backed by an allowlisted analytics layer.
The GitHub worker's existing sequence and signed delivery keep authentication
and duplicate handling in one place. A separate worker would need its own
routing, credentials and consistency rules. An analytics index would duplicate
history and need invalidation rules. Neither is needed for the initial queries.
The accepted checkpoint remains the source of truth. Each request still
consumes its normal bridge sequence and records a signed delivery.

Read the authority and narration state from a SQLite read transaction. Verify
the registered package and its signed ancestry, then query the database through
a read-only connection. Reconstruct only the database from immutable chunks in
disposable storage after releasing the authority transaction. This avoids
pinning the worker's materialized cache during a read. Pages
bind the checkpoint, narration visibility and original filters. Resume on the
same state or restart the query if the career or narration has moved.

The first release targets registered multi-season checkpoints. It shares the
simulation's competition rules and leaves legacy historical match retrieval
with `historical_results`.

## Protocol compatibility

The registered table and finance views can return `edition` and
`account_unknown`. Protocol 2 accepts both fields alongside the new
`career_statistics` result. Old envelopes and signed deliveries retain their
existing format.

## Data inventory

| Area | Recorded or derivable | Coverage and initial API |
| --- | --- | --- |
| Match scores, dates, brackets and aggregates | Native `fixtures`, Copa do Brasil legs, 2027 continental tables, `world_finals`, `world_fixtures`, `ms_fixtures` and `ms_ties`. `results.Projection` deduplicates mirrors and reads recorded outcomes. | Existing `historical_results` supports history and recent-match questions. Earlier historical dates and results can be incomplete. |
| Tables and qualification | Native league data, committed group fixtures and draw receipts, edition entries, ties and qualifications. `multiseason.groups.table` and `competitions.standings` implement the ranking. | `standings` covers registered leagues and committed continental groups, including incomplete groups. Rankings sort by points, wins, goal difference, goals for and stable club ID. No head-to-head criterion in this policy. Qualification slots describe the current position; actual progression remains in recorded brackets and qualifications. Carioca pool standings and native-only league tables need adapters. |
| Player match output | `world_performances.performance_json` and `ms_executions.result_json.performances` store player and club IDs, starts, seconds, goals, assists, shots, shots on target, xG, saves, cards, injuries and ratings. | `player_stats` combines the forward and multi-season rows. Native `player_matches`, `player_season_totals`, cup and continental appearance tables use different schemas and remain excluded. Coverage counts disclose missing performance rows. |
| Player identity and attributes | `world_players` stores club, OVR, position and ability values. `world_player_state` stores time-stamped fitness, morale, form, registration and injury observations. `world_discipline` records competition counters and bans. `ms_lifecycle` records modeled age and status where present. | `squad` returns stored observations and flags modeled player identity. Fitness is measured at `observed_at`; elapsed recovery is not projected. A loan, retirement or unregistered player can retain a club association, so use registration and lifecycle state when reporting the active squad. |
| Development and player value | `ms_attributes` records explicit before/after annual updates. Match inputs also capture attribute snapshots. Some market decisions contain proposed fees. | `development` exposes annual changes. Continuous attribute history, normalized market value and potential need a separate model or projection. A proposed fee is specific to a transaction. |
| Team performance and tactical history | Score-based home/away records and clean sheets are derivable. Forward bundles store shots and events, and committed match inputs plus plans or previews provide formation/manager evidence where available. `MatchResult.possession_home` is generated in regulation and is not a field of the registered resolved bundle. | `team_record` returns score-based performance. Team xG, shot trends, formations and manager comparisons can be added from persisted evidence. Possession requires source-specific validation and possibly new instrumentation. |
| Contracts, transfers and finance | Native `transfers`, `transfer_contracts`, `finance_ledger` and `finance_budget`; registered `ms_contracts`, `ms_transfers`, `ms_loans`, `ms_accounts`, `ms_ledger`, payroll and obligations. | `transfers` lists recorded multi-season transactions. `squad` shows an active contract when present. `current_finances` remains the Vasco finance view. Historical native transaction reconciliation, loan options, cash and budget time series are future projections. |
| Derived metrics with gaps | A saved shot may name an actual awarded assist. Knockout resolution separates shootout attempts from match goals. Some legacy native event types use different conventions. | Expected assists, player clean sheets, own-goal attribution across all profiles, penalty splits, injury duration histories and keeper claims require additional definitions or data. Goals/assists here follow the saved performance rows. No figures are inferred from score lines or narrative text. |

Appearances count stored starters or players with positive playing time. Minutes
are seconds divided by 60. xG sums stored shot xG credited in the performance
record. xG per 90 equals total xG times 5,400 divided by played seconds; it is
null at zero seconds. Mean rating weights each included appearance equally.
Team wins/draws/losses use the stored match score including extra time and
excluding shootouts. Home/away is the fixture designation, including neutral
fixtures. Zero denotes a recorded zero within the selected coverage. Null means
unknown or absent for optional attributes and contracts, and not applicable for
xG per 90 at zero seconds. Missing metrics are omitted from the supported metric
list. Empty results carry coverage metadata and do not assert a zero career total.

## Hikari requests

Read the live private bridge status and use the usual protocol-2 issue envelope
with `command: "career_statistics"`. Send one of these `args` objects.

```json
{"dataset":"standings","competition":"LIB","season":2028,"group":5}
```

```json
{"dataset":"player_stats","club":"Vasco","season":2028,"sort":"xg_per_90","min_minutes":180}
```

Other examples include `{"dataset":"editions","season":2028}`,
`{"dataset":"squad","club":"Vasco","sort":"ovr"}`,
`{"dataset":"player_stats","player":"Nuno Moreira","season":2028}`,
`{"dataset":"team_record","club":"club:15","season":2028,"competition":"LEAGUE"}`,
`{"dataset":"development","season":2028,"club":"Vasco","sort":"ovr_delta"}` and
`{"dataset":"transfers","club":"Vasco","date_from":"2028-01-01"}`.
Club and player names are case-insensitive exact matches. For ambiguous names,
use the stable ID returned by the error. Use edition competition codes and exact
stage codes such as `GROUP:5` for filters. Missing season means the current
season for standings and all available recorded seasons for player/team totals.

The result is under `result.career_statistics` with `accepted_checkpoint`,
`accepted_clock`, `database_sha256`, `filters`, `coverage`, `rows`,
`total_rows` and `next_cursor`. Group rows include rank, club/name, points,
played, wins/draws/losses, goals for/against and goal difference. For example,
the fixture inventory at episode #106 yields coverage
`{"edition":"LIB:2028","group":"GROUP:5","played_fixtures":6,"scheduled_fixtures":12,"complete":false}`
alongside season, ranking and qualification information.

`limit` is 1–30, default 20, with an additional 30 KB row budget. Send
`{"cursor":"<next_cursor>"}` alone in a fresh read issue to get the next page.
`SNAPSHOT_MOVED` means restart with original filters against the new head.
`NARRATION_PENDING` indicates an accepted result is withheld by the query.
Reads do not advance or reveal it. A stored injury date and registration state
also depend on visibility, so squad, development and transfer views wait while
accepted match narration is pending. A completed empty page with limited
coverage cannot support a conclusion about missing seasons.

## Integration

Worker 0.13.7 uses the existing protocol-2 ledger and needs no save or schema
migration. Its signed status advertises `worker_version` and
`career_statistics_available`. Operators can verify those fields and compare
the accepted checkpoint and next sequence without submitting a bridge request.

Before restarting, acquire the worker's poll lock and verify that the sealed
ledger has no incomplete requests or deliveries, the accepted head has no
outstanding claim, and the private queue is empty. Keep the lock until the old
process exits. Retain the verified prior wheel and task configuration for
software rollback. Preserve the current authority and ledger during rollback.

Each page reconstructs one database in temporary storage and scans the relevant
fixtures. Queries share the sequential bridge queue. Career-wide totals may
take longer than a single group table.
