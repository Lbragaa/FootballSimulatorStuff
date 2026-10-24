# Inherited issues at Save 046

All findings below are preserved. The normal audit exits successfully when canonical history is unchanged and prints warnings; `--strict` fails on these warnings. The full byte/table fingerprints ensure new changes cannot hide behind known warnings.

| Issue | Verified evidence / limitation | Future handling |
|---|---|---|
| Overdue cup ties | 8 Libertadores R16 ties dated Aug 31/Sep 7; 8 Sudamericana playoffs dated Aug 26/Sep 2; 4 CDB QFs dated Sep 15/Sep 22, all scheduled and unplayed at Sep 26 | 046C calendar reconciliation, with explicit old/new dates and conflict checks; no invented scores |
| Payroll | Seven incremental payroll debits Jan–Jul, R$1.38m each; August absent; September absent at Sep 26 | Contract-backed reconciliation, unique period keys; choose/document September month-end/proration policy; no duplicate annual/cash charges |
| Board objectives | All six `achieved` flags remain pending, including concluded cup objectives; Finance objective still says R$55m despite approved R$68m | Evidence-backed status and wording reconciliation in a new checkpoint |
| Partial 2026 coverage | 71 recorded league fixtures rather than 380; final table archive has 20 rows | Use final archive for final standings; unknown games/events remain unknown |
| Missing dates | 39 completed main-table fixtures have NULL or non-ISO dates | Display unknown dates; do not fabricate or infer exact historical dates |
| Card timing | 22 joined card events occur after a starter's recorded exit minute | Preserve evidence, flag historical quality; future engine must enforce on-field eligibility and exact event sequence |
| Engine audit gaps | 169 of 170 `match_engine_audit` rows have both prematch xG values zero/NULL; 80 completed 2027 league fixtures lack an audit row | No backfilled invented metrics; future engine must record actual prematch parameters and seeds |
| Savarino identity | #196 is named `Jefferson Savarino [historical Botafogo archive]`; resolution maps it to active #354. Both currently carry `club_id=5` (Fluminense) | Archive metadata/resolution, not club ID alone, must block #196 from future selection; preserve historical appearances |
| Legacy execution | Reference module performs copy/setup/simulation at module top level; episode scripts use `/mnt/data`, source slicing, `.replace()` and `exec` | Treat as historical evidence; future modular engine uses explicit APIs and configuration, forward only |
| JSON tied-minute order | `results046.json` presents Rojas GOAL before SUBSTITUTION at 82, due to tuple sorting; DB event IDs 2811/2812 and episode have correct order | Preserve the original JSON; consumers should use database sequence, not assume list ordering is valid |

Several older `meta` notes are also stale (preseason, league round, financial and competition notes). The CLI derives current progress from structured tables, not those narrative notes. Reconcile obsolete metadata only in an authorized new checkpoint.

The historical card query detects cards strictly after recorded starter exit minutes. It is not a complete reconstruction of all historical on-field states; minute-only data can be ambiguous at ties, stoppage time and for bench discipline. Current audit explicitly checks Rojas' correct database order, and checks R25 accounting, but it is not a new match-engine event validator for every competition.

SQLite foreign-key validation passes for declared keys; many legacy tables have no declared constraints. Full logical hashes protect their inherited contents, rather than proving every historical relationship or metric is semantically complete. Reproducibility of historical engines is limited by missing prematch inputs and legacy execution patterns. No historical replay was attempted.
