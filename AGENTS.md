# THE BRAGA ERA — durable engineering instructions

## Authority and scope

- This is an existing fictional universe, not a new simulation. SQLite is the structured source of truth. Documentation supplies context and limitations. Do not import real-world rosters/results automatically.
- Phase 0 ends at Save 046, fictional date 2027-09-26 23:30. Do not create 046C/047, simulate matches, advance time, implement a replacement engine or build a dashboard unless a subsequent user request authorizes that scope.
- Vasco 3–2 Palmeiras (2027 R25, fixture 322) is final. Never reroll it. Next Vasco match is Mirassol away, October 3, R26, unplayed.
- Do not execute or import the handoff's reference/build/episode scripts: they perform top-level writes, use absolute paths and exec/text substitution. The reviewed `data/handoff/tools/verify_handoff.py` is the sole legacy executable permitted for Phase 0 and must run without Python optimization (`-O` disables its assertions).

## Data protection

- Preserve `BRAGA_ERA_HANDOFF_AFTER_046.zip` byte for byte. Reproduce extraction using `tools/bootstrap_handoff.py`. Never edit the extracted handoff, its manifest or its nested backups.
- Use `braga_era.db.connect_read_only` for canonical queries. No canonical UPDATE, INSERT, DELETE, migrations or tests that write into the handoff.
- `braga_era/baselines/save046.json` is a frozen historical reference, not a generated cache. Never regenerate or weaken it to make tests pass. Any later checkpoint must retain the 046 baseline and add an explicitly reviewed profile.
- Completed historical scores, events, transfers and identities are immutable. Missing information stays unknown. Known defects must be documented, not silently corrected.
- Archive Savarino #196 and active #354 separately. Both currently have club_id=5; club membership does not establish eligibility. Read `player_identity_resolution` and archive identity metadata; preserve historical attribution.
- Distinguish ledger cash from approved category headroom, annual commitments from monthly cash debits, and recognized capital from plans. August payroll and September policy remain unresolved.

## Engineering and verification

- Python 3.11+, standard library at runtime; pytest for tests. Paths must be portable; explicit database arguments override environment/default paths.
- Run `python tools/bootstrap_handoff.py`, `python -m braga_era inspect`, `python -m braga_era audit`, and `python -m pytest` for relevant foundation changes. Expected known warnings are not evidence of a clean football calendar.
- Test mutations exclusively on temporary databases/copies. Confirm original ZIP and DB SHA256 remain unchanged. Use meaningful tampering, write-denial and portability tests.
- Update README and documents when commands, behavior or verified facts change. Distinguish facts verified from SQLite, documentary context and proposals.
- Future official simulations must precommit engine/configuration/seed, preserve coach autonomy and genuine uncertainty, persist events once, validate before promotion, and narrate chronologically without outcome spoilers. Forecasts must never enter official fixture records.
