# Historical results and complete competition reporting

`historical_results` retrieves the accepted career's existing records without
executing football, accepting a checkpoint, moving time, consuming narration or
changing a cursor. It works with automatic gameplay disabled and needs only read
scope. There is no new archive that starts at installation: old source tables
and future `world_fixtures` are projected on demand.

## Commands and arguments

Use the existing `braga-bridge-2` request envelope, pinned GitHub account, current
career/head/sequence and a fresh UUID. Set command to `historical_results` and
args to any of these optional fields. Extra fields are forbidden by the schema.

| Argument | Type / behavior |
| --- | --- |
| competition | Human name or alias: Brasileirão/LEAGUE, Copa do Brasil/CDB, Libertadores/LIB, Sul-Americana/Sudamericana/SULA, Carioca; other names recorded in generic fixture tables also work |
| season | Integer 1900–2200; reports only recorded seasons, never invents a season |
| round | Integer 1–99; normalizes R01/R29 and numeric legacy round labels |
| stage | Recorded stage or Portuguese/English alias: QF/Quartas, SF/Semifinais, FINAL, R16/Oitavas, R32, PO/Playoffs, GROUP |
| leg | 1 or 2; independent of whether the full stage is complete |
| date | Exact YYYY-MM-DD; mutually exclusive with range fields |
| date_from, date_to | Inclusive real ISO dates; unknown dates cannot match a date filter |
| club | Recorded human club name (accent-insensitive) or an established alias such as Vasco da Gama; no fixture key needed |
| recent | 1–500; most recent recorded completed matches by recorded date, descending; undated records sort last |
| limit | 1–50 per page, default 20; byte limits can yield a smaller page |
| include_pending | Boolean, default false; expose scheduled/conditional/postponed records with no invented scores |
| cursor | Unchanged opaque next_cursor from the prior page; use alone or repeat exactly the original filters |

Examples:

```json
{"competition":"Brasileirão","season":2027,"round":29,"limit":50}
{"competition":"Brasileirão","season":2027,"round":28,"limit":50}
{"competition":"Libertadores","season":2027,"stage":"QF","leg":1,"date_from":"2027-10-01","date_to":"2027-10-31"}
{"competition":"Libertadores","season":2027,"stage":"QF","include_pending":true,"limit":50}
{"competition":"Copa do Brasil","season":2027,"stage":"QF","limit":50}
{"competition":"Copa do Brasil","season":2027,"recent":10}
{"club":"Flamengo","season":2027,"limit":50}
{"club":"Vasco","season":2027,"recent":10}
{"date_from":"2027-10-01","date_to":"2027-10-31","limit":50}
{"competition":"Brasileirão","season":2027,"limit":50}
```

No special startup, authenticator, token or manual file transfer is required.
Normal Hikari continuation remains one `play_next_episode` command, not a chain
of historical calls. Explicit historical requests use this read command.

## Response and pagination

The signed result contains `historical_results` plus the current outer
`accepted_checkpoint`. The nested object provides:

- authenticated accepted checkpoint/database hash, clock, career, mode and
  `read_only:true`;
- matches with dates (null if unknown), competition/season, round/stage/leg,
  named club identities, recorded status, score, resolution and source IDs;
- ties with orientation-specific aggregates, recorded qualifiers and deciding
  penalty/extra-time information when actually recorded;
- selection counts/completeness, unknown-score count, recorded coverage,
  limitations, offset, returned count, has_more and next_cursor.

For `has_more:true`, send a fresh normal request whose args are
`{"cursor":"<next_cursor>"}`. Continue until false before claiming a full season
was shown. A cursor pins checkpoint, filters, offset and Vasco reveal visibility
under a career/mode-bound HMAC. Accepted newer checkpoints do not reorder an old
page. A fresh query sees newer results. Use the OUTER current head for the next
request envelope; the nested head identifies the immutable reporting snapshot.
Tokens contain no seed/key/path and are never narration cursors.

Unknown names return UNKNOWN_COMPETITION / UNKNOWN_CLUB. Unsupported/invalid
filters have typed validation errors; malformed command envelopes are rejected
by the established protocol. INVALID_CURSOR, CURSOR_FILTER_MISMATCH and
UNREGISTERED_CHECKPOINT fail closed. An empty real selection returns an explicit
notice and zero matches, not fabricated scores. Conflicting source mirrors
return SOURCE_SCORE_CONFLICT rather than silently choosing a result.

## Source inventory and historical coverage

| Source | Mapping and limits |
| --- | --- |
| `fixtures` | General club fixtures: Brasileirão 2026/2027, CDB 2026, Carioca 2027 and future recorded competitions. No season column: use explicit competition year, recorded kickoff year or linked cup_ties season. Never guess a missing day. |
| `cup_ties` | Legacy linked fixture IDs, leg orientation, recorded aggregates and winner club IDs; native status vocabulary includes complete. |
| `cdb_2027_legs` + `cdb_2027_bracket` | Compound `(tie_code,leg)` identity, hg/ag scores, stage, club names, recorded winner; complete/completed/pending qualifiers are distinct. |
| `libertadores_2027_fixtures` | Group fixtures use home_goals/away_goals and matchday. |
| `sudamericana_2027_fixtures` | Group fixtures use hg/ag; do not assume Libertadores columns. |
| `libertadores_2027_round_of_16` | Leg result strings and reversed home orientation on L2. Future official forward mirrors take precedence only by the exact shared source identity. |
| `sudamericana_2027_playoffs` | Pairings/dates/winner metadata. Missing leg scores are not reconstructed from winner or group outcomes; forward leg rows supply recorded scores. |
| `world_finals` | Existing 2026 continental/CDB finals with score, optional penalties and provenance. fixture_id links deduplicate the CDB final already in fixtures. Preserve the archive's “fictional conditional final” provenance; do not reclassify it as a newly simulated final. |
| `world_fixtures`, `world_receipts`, `world_ties` | All existing forward results, future scheduled/conditional entries, result hashes, aggregate orientation and established qualification. Source mirrors replace native duplicates. |
| `world_draws` | Activated reservations are superseded by their established fixtures; undrawn reservations remain conditional, not invented matches. |
| `world_events` + signed authority cursors | Reveal-completion check only. No goals are counted from events to manufacture a score; no narration/session writer is called. |

`cup_summary`, `competition_history`, group outcomes and standings archives are
aggregate/qualification context. They cannot supply missing per-match scores and
are not expanded into invented fixtures. Player appearances, current rosters and
news are not score sources.

Verified current coverage includes:

- Brasileirão 2027: all 380 recorded fixtures, with completed versus scheduled
  clearly separated; 2026: only 71 retained fixtures (late rounds plus a
  postponed match), not a fabricated complete 2026 season.
- CDB 2027: available R32/R16 history and all forward knockout paths; 2026: the
  five retained semifinal/final fixtures only.
- Libertadores and Sul-Americana 2027: all 96 group fixtures each, retained
  knockout metadata and every accepted/generated forward leg; 2026: each
  retained final only, no invented earlier continental rounds.
- Carioca 2027: five retained semifinal/final matches, consistent with the
  existing final-four simplification; no invented group stage.

There are 39 genuinely undated early 2027 league fixtures (nine in R02 and all of
R03–R05). They remain accessible without date filters. Report missing score,
penalty or extra-time details as unknown. Name-only legacy clubs retain explicit
historical name identities where no existing club/alias resolves them. Modeled
clubs keep their existing persistent IDs; Vasco is club:15, not club:5.

## Episode presentation

After Vasco's chronological final whistle/statistics, `episode_results` contains
all ten rodada fixtures/scores when recorded, pending entries when incomplete,
other relevant completed fixtures/legs, aggregates and confirmed qualifiers.
Standings follow. A completed first leg can be reported immediately; a whole
stage need not have finished. Existing consolidated stage milestones remain.

The reporting section has its own bounded allowance inside the existing 55 KB
result/60 KB signed-comment bounds. `omitted`, `omitted_ties`, `exhaustive:false`
and pinned retrieve_all/retrieve_round pages explicitly disclose any truncation.
Do not call a partial list exhaustive or a partial round final. A size-bound
unfinished Vasco timeline gets results_deferred instead of other scores before
the whistle; its deferred IDs persist into the bounded continuation. Old cached
episode responses remain unchanged; their missing details are now retrievable
through historical_results.

Historical requests do not expose candidates or private diagnostics. A forward
Vasco fixture whose final page is still unrevealed withholds its score and tie
outcome (`score_availability:narration_required`). Historical retrieval cannot
move or bypass that cursor. Already narrated historical scores are available
normally at any later point in the career.

## Verification and deployment evidence

The exact current accepted head was inspected rather than assuming 046C was
still current. Local read-only acceptance checks returned all ten R29 results,
including the established Vasco 2–2 Flamengo; four Libertadores QF first legs;
and eight CDB QF legs with four recorded semifinalists. Registry and cursor hashes
were identical before/after. No official matches are run to test this feature.

Automated regression evidence, disconnected episode rehearsals, installed wheel
hash and private transport acceptance results are recorded with the task/PR and
ignored local verification artifacts. Cross-platform CI must be read from its
actual current run; an earlier green episode build is not proof of this revision.
