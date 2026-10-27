# THE BRAGA ERA — durable engineering instructions

## Authority and scope

- This is an existing fictional universe, not a new simulation. SQLite is the structured source of truth. Documentation supplies context and limitations. Do not import real-world rosters/results automatically.
- Task 03A explicitly accepts exact Save 046C v2 as the administrative canonical checkpoint and authorizes the first headless engine plus disposable NONCANONICAL demonstrations. Accepted DB SHA256 is `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`; ZIP SHA256 is `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`. Approval is external to those immutable bytes; see `docs/acceptance/046C_v2_approval.json` and the `save-046c-v2` GitHub Release. No official match, Save 047 or fictional time advance is authorized. The fictional date remains 2027-09-26 23:30.
- Vasco 3–2 Palmeiras (2027 R25, fixture 322) is final. Never reroll it. Next Vasco match is Mirassol away, October 3, R26, unplayed.
- Do not execute or import the handoff's reference/build/episode scripts: they perform top-level writes, use absolute paths and exec/text substitution. The reviewed `data/handoff/tools/verify_handoff.py` is the sole legacy executable permitted for Phase 0 and must run without Python optimization (`-O` disables its assertions).

## Data protection

- Preserve `BRAGA_ERA_HANDOFF_AFTER_046.zip` byte for byte. Reproduce extraction using `tools/bootstrap_handoff.py`. Never edit the extracted handoff, its manifest or its nested backups.
- Use `braga_era.db.connect_read_only` for canonical queries. No canonical UPDATE, INSERT, DELETE, migrations or tests that write into the handoff.
- Administrative writes belong only in unpublished scratch copies via the explicit versioned migration. Every candidate must authenticate its parent, commit all changes transactionally, replay its permitted delta independently and publish atomically after validation.
- Preserve the 046 baseline permanently. `profiles/save046c_plan.json` is rejected v1 and must remain unchanged; `profiles/save046c_plan_v2.json` is the revised, independently validated planning proposal. Neither is a cache to regenerate for failing tests. Changes require explicit profile revision, re-solving, feasibility review and a new unaccepted artifact.
- Keep output databases/ZIPs under ignored `output/`. Never commit accumulating save binaries. Exported packages contain a verified parent, manifests, operation before/after records and reports; restore to new directories only.
- The v1 holiday calendar is rejected and unpromotable. Accepted v2 has 70 future kickoff changes (36 dates, 34 times), protects Mirassol–Vasco on October 3 16:00, keeps all cups in 2027 and respects the December 22–January 5 blackout. It introduces no sub-72h interval and retains the approved inherited 69h Coritiba exception. The 72h policy includes travel; actual routes/foreign calendars remain unknown. Task 03A approves this scope, contract-based payroll accounting and evidence-backed objectives.
- The explicit promotion API registered the exact approved v2 once under Task 03A. Do not manufacture a new accepted hash from a platform rebuild. Install the released ZIP with `tools/bootstrap_accepted.py`; it authenticates the exact ZIP/DB and never promotes. Tests use temporary registries only. Keep immutable package `candidate` metadata unchanged; acceptance is the external receipt/catalog/registry.
- `braga_era/baselines/save046.json` is a frozen historical reference, not a generated cache. Never regenerate or weaken it to make tests pass. Any later checkpoint must retain the 046 baseline and add an explicitly reviewed profile.
- Completed historical scores, events, transfers and identities are immutable. Missing information stays unknown. Known defects must be documented, not silently corrected.
- Archive Savarino #196 and active #354 separately. Both currently have club_id=5; club membership does not establish eligibility. Read `player_identity_resolution` and archive identity metadata; preserve historical attribution.
- Distinguish ledger cash, authority, annual commitments and monthly expense. Original 046 is unreconciled; candidates pay August once (R$1.38m), preserve R$30.55m cash, accrue September R$1,559,000.01 with no September cash, and retain the R$16m reserve. Do not invent missing base payroll or capital.

## Engineering and verification

- Python 3.11+, standard library at runtime; pytest for tests. Paths must be portable; explicit database arguments override environment/default paths.
- Run `python tools/bootstrap_handoff.py`, `python -m braga_era inspect`, `python -m braga_era audit`, and `python -m pytest` for relevant foundation changes. Expected known warnings are not evidence of a clean football calendar.
- For checkpoints also run `audit --profile 046C --db CHECKPOINT_DB --parent ORIGINAL_DB` and `save verify DIRECTORY_OR_ZIP`. Audit automatically selects the recorded version's strict registered profile; an explicit `--profile 046` must still reject 046C. It never changes a baseline or profile to accept a different artifact.
- Test mutations exclusively on temporary databases/copies. Confirm original ZIP and DB SHA256 remain unchanged. Use meaningful tampering, write-denial and portability tests.
- Update README and documents when commands, behavior or verified facts change. Distinguish facts verified from SQLite, documentary context and proposals.
- Future official simulations must precommit engine/configuration/seed, preserve coach autonomy and genuine uncertainty, persist events once, validate before promotion, and narrate chronologically without outcome spoilers. Forecasts must never enter official fixture records.

## Phase 2A engine

- `braga_era/engine` separates immutable snapshots, versioned configuration, named RNG streams, autonomous coaches, pure match execution, independent replay audit, read-only world adapters and narration. Do not use source-code patching, `exec`, SQL writes, UI dependencies, wall-clock seeds or outcome searches inside the engine.
- Both teams select current eligible database IDs. Enforce archived #196, injuries and supplied suspension exclusions. The source has no reliable suspension register; do not invent historical bans. No particular starter or Vasco success is guaranteed. The historical R25 -0.06 training modifier has expired.
- `sandbox` uses an unchanged disposable copy and labels every result NONCANONICAL TEST SIMULATION. Hash source and scratch before/after, validate all events, retain the seed commitment written before draws, and refuse existing output directories. `narrate` advances a stored sequence and releases postmatch data only at the final whistle; private diagnostic JSON contains spoilers.
- Foreign continental clubs have no recorded player rosters. Fail with `MissingRoster`; do not invent contemporary real-world players or ratings. Task 03A uses league:333 and synthetic Vasco–Fluminense instead. The official global agenda must begin with September 30 continentals before October 3 Vasco; missing roster evidence blocks that future runner.
- Competition adapter/progression/player-state protocols are future integration boundaries, not official implementations. Extra time/shootouts and official persistence fail closed. Fitness in sandbox snapshots is observed checkpoint fitness without assumed intervening recovery.
- Preserve engine/config/seed policy versions. Changes affecting outcomes require a documented forward version/calibration decision, never rerolling accepted history. CI authenticates released 046C bytes, tests Windows/Linux Python 3.11–3.13 and compares the two NONCANONICAL regression reports.
