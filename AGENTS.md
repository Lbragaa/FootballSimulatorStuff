# THE BRAGA ERA — durable engineering instructions

## Authority and scope

- This is an existing fictional universe, not a new simulation. SQLite is the structured source of truth. Documentation supplies context and limitations. Do not import real-world rosters/results automatically.
- Accepted canonical state remains Save 046, fictional date 2027-09-26 23:30. Task 02 authorizes an isolated, fully validated candidate 046C only. Do not promote it, create 047, simulate matches, advance time, implement a replacement engine or build a dashboard without a subsequent explicit request.
- Vasco 3–2 Palmeiras (2027 R25, fixture 322) is final. Never reroll it. Next Vasco match is Mirassol away, October 3, R26, unplayed.
- Do not execute or import the handoff's reference/build/episode scripts: they perform top-level writes, use absolute paths and exec/text substitution. The reviewed `data/handoff/tools/verify_handoff.py` is the sole legacy executable permitted for Phase 0 and must run without Python optimization (`-O` disables its assertions).

## Data protection

- Preserve `BRAGA_ERA_HANDOFF_AFTER_046.zip` byte for byte. Reproduce extraction using `tools/bootstrap_handoff.py`. Never edit the extracted handoff, its manifest or its nested backups.
- Use `braga_era.db.connect_read_only` for canonical queries. No canonical UPDATE, INSERT, DELETE, migrations or tests that write into the handoff.
- Administrative writes belong only in unpublished scratch copies via the explicit versioned migration. Every candidate must authenticate its parent, commit all changes transactionally, replay its permitted delta independently and publish atomically after validation.
- Preserve the 046 baseline permanently. `profiles/save046c_plan.json` is the reviewed deterministic proposal, not a cache to regenerate for failing tests. Changing calendar policy/dates requires re-solving, feasibility review and rebuilding the unaccepted candidate under a reviewed profile.
- Keep output databases/ZIPs under ignored `output/`. Never commit accumulating save binaries. Exported packages contain a verified parent, manifests, operation before/after records and reports; restore to new directories only.
- Candidate 046C has commissioner decisions pending: 72-hour kickoff-to-kickoff rest includes travel, 12 inherited league shortfalls stay fixed, year-end holiday rounds/finals and long inter-leg gaps, and actual-day/month-end incremental payroll policy. Do not present this as an unqualified globally conflict-free calendar or accepted accounting policy.
- The promotion API is an explicit future acceptance gate requiring candidate/parent hashes and all policy approvals. There is no promotion CLI in Phase 1; never call it against the real registry during this task. Tests use temporary registries only.
- `braga_era/baselines/save046.json` is a frozen historical reference, not a generated cache. Never regenerate or weaken it to make tests pass. Any later checkpoint must retain the 046 baseline and add an explicitly reviewed profile.
- Completed historical scores, events, transfers and identities are immutable. Missing information stays unknown. Known defects must be documented, not silently corrected.
- Archive Savarino #196 and active #354 separately. Both currently have club_id=5; club membership does not establish eligibility. Read `player_identity_resolution` and archive identity metadata; preserve historical attribution.
- Distinguish ledger cash from approved category headroom, annual commitments from monthly cash debits, and recognized capital from plans. August payroll and September policy remain unresolved.

## Engineering and verification

- Python 3.11+, standard library at runtime; pytest for tests. Paths must be portable; explicit database arguments override environment/default paths.
- Run `python tools/bootstrap_handoff.py`, `python -m braga_era inspect`, `python -m braga_era audit`, and `python -m pytest` for relevant foundation changes. Expected known warnings are not evidence of a clean football calendar.
- For candidates also run `audit --profile 046C --db CANDIDATE_DB --parent ORIGINAL_DB` and `save verify DIRECTORY_OR_ZIP`. Normal audit defaults to the strict 046 profile; do not weaken it to accept 046C.
- Test mutations exclusively on temporary databases/copies. Confirm original ZIP and DB SHA256 remain unchanged. Use meaningful tampering, write-denial and portability tests.
- Update README and documents when commands, behavior or verified facts change. Distinguish facts verified from SQLite, documentary context and proposals.
- Future official simulations must precommit engine/configuration/seed, preserve coach autonomy and genuine uncertainty, persist events once, validate before promotion, and narrate chronologically without outcome spoilers. Forecasts must never enter official fixture records.
