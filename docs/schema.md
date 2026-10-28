# Canonical schema guide

Task 03C leaves canonical schema unchanged. Explicit readiness policies add `world_blobs` (verified content-addressed journal values), `world_draws` (pre-draw commitments/pairings), and `world_champions` (completed-final/ranking evidence). The separate authority registry has authority, batches, signed decisions, unique parent/fixture and obligation claims, and accepted candidate hashes. It is never installed into accepted 046C. See [readiness report](task03c_report.md).

Task 03B adds a separate development-only world schema on copies of exact 046C v2; accepted schema/data are unchanged. Its 16 tables are explicitly enumerated in `braga_era/world/schema.py`: world info, clubs, players, player state, discipline, training, fixtures, ties, batches, executions, receipts, events, performances, obligations, operations and cursors. See [world architecture](world_integration.md) for mapping and limitations. Legacy `world_finals`/`world_final_events` are historical tables, not part of that additive inventory. Forward detailed statistics live in the normalized world layer while native fixture/leg/status/standing mirrors are updated under the development profile.

The original database has 64 user tables and one SQLite internal table. See [exact DDL inventory](schema_inventory.md); Phase 0 adds no tables, indexes, triggers or migrations.

Candidate 046C preserves that original schema and adds seven administrative tables, for 71 user tables. The DDL and its hash are explicit in `braga_era/migrations.py`; candidate DDL is also listed in [046C schema inventory](schema046c_inventory.md). New tables never replace historical sporting tables:

| Candidate table | Purpose / key |
|---|---|
| `checkpoint_info` | Version, immutable parent SHA256, schema/profile/plan hash, candidate status |
| `schema_migrations` | Schema version, unique migration identifier, DDL SHA256 |
| `admin_operations` | Stable operation IDs and sequenced keyed before/after records |
| `calendar_events` | Known scheduled cup legs and conditional later-round reservations; exact kickoffs and potential qualifier pools |
| `admin_policies` | Explicit proposed calendar and incremental payroll conventions |
| `payroll_periods` | Unique monthly obligation registration and unique link to a cash ledger row |
| `payroll_obligations` | Contract/player-level covered dates and integer-cent due/accrued amounts |

| Domain | Principal tables and cautions |
|---|---|
| Save metadata | `meta(key,value)`; version/date/next fixture are current, several old descriptive notes stale |
| Domestic league | `clubs` running standings; `league_participants(season,club_id)` defines the season's 20 clubs; `fixtures` carries historical and 2027 matches |
| Match detail | `events`, `shots`, `player_matches` join via `fixtures.id`; events' integer IDs preserve tied-minute insertion order |
| Players | `players.id` is identity, not name; `player_season_totals` keys season/competition/player; aggregate player counters may mix years/competitions |
| Identity and eligibility | `player_identity_resolution(archived_id,canonical_id)`; archive name signals historical identity; no universal active boolean |
| Form / coaching | `match_form_profile`, `player_form_snapshot`, `player_postmatch_impact`, `tactical_match_log`, `training_microcycles_2027` |
| Auditing | `match_engine_audit`, `match_shot_detail`, scouting/rating audits; historical zeros are not observed metrics |
| Copa do Brasil 2027 | `cdb_2027_bracket`, `cdb_2027_legs`, events, shots and performance are separate from `fixtures`; leg key is `(tie_code,leg)`; mixed `complete` / `completed` status vocabulary |
| Libertadores | `libertadores_2027_*` participant, group, fixture, outcome and R16 tables; group fixture scores use `home_goals/away_goals` |
| Sudamericana | `sudamericana_2027_*`; group fixture scores use `hg/ag`; playoffs have no results yet |
| Continental detail | `continental_match_*`, `continental_player_matches`, calendar actions and qualifications; do not assume all competitions share ID namespaces |
| Finance | `finance_ledger` cash by account; `finance_budget` authorization/commitment by category; assumptions, ownership and capital decisions document approved sources |
| Market | `transfers`, `transfer_contracts`, `market_negotiations_2027`; contract annual obligation differs from cash payroll expense |
| Archives / cups | `league_standings_archive`, `competition_history`, `world_finals`, `world_final_events`, `cup_summary`, `cup_ties`; 2026 game coverage remains partial |
| Decisions / narrative | `decisions`, `news`, `board_objectives`, `season_rules`; prose is contextual, not authority to override settled outcomes |

Ranking convention in the inherited scripts: points, wins, goal difference, goals scored (descending), club name as a deterministic final fallback. The project preserves that convention; it does not import a contemporary competition rulebook.

`fixtures.competition='Brasileirão'` identifies recorded 2026 league history; `Brasileirão 2027` identifies the 380-fixture 2027 season. Filtering solely by `clubs` or a round label can mix unrelated seasons. Separate continental/CDB tables must be included when reporting universe-wide coverage.


## Task 03D authority schema

The football schema is unchanged. A separate authority SQLite registry holds signed career/model identity, stable seed, active transfer lease, accepted-parent head, batch and unique parent/fixture/obligation claims, authorization/acceptance decisions, signed cursor revisions and idempotent narration pages. Accepted payloads contain the inherited football database and a signed proof chain. Registry path locators may change on verified restoration; immutable checkpoint identities do not. No Task 03D migration writes into accepted 046C. See [report](task03d_report.md).
