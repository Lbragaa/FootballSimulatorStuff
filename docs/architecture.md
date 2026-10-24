# Foundation architecture

The original ZIP is the versioned source artifact. `tools/bootstrap_handoff.py` authenticates its pinned SHA256 and internal manifest, checks paths, CRCs, duplicate paths, symlinks, total size and existing contents, then reproduces it under `data/handoff/`. Nested ZIPs remain opaque backups; no recursive extraction or legacy simulation runs occur. Extraction is byte-reproducible and idempotent, rather than dependent on OS archive metadata.

`braga_era` is a flat-layout Python package so `python -m braga_era` works from a checkout without installation. Its modules have narrow responsibilities:

| Module | Responsibility |
|---|---|
| `config.py` | Explicit path > `BRAGA_ERA_DB` > repository-relative default |
| `db.py` | URI-escaped read-only connection, query-only mode, denied write/attach operations, streaming file SHA256 |
| `state.py` | Structured state and standings queries, competition evidence, budget headroom |
| `history.py` | Stable UTF-8 JSON serialization, logical table hashes, completed fixture snapshot, packaged baseline loading |
| `audit.py` | Reusable report/finding objects, checkpoint and derived invariants, inherited warnings |
| `cli.py`, `__main__.py` | Text/JSON CLI, exit status handling |
| `baselines/save046.json` | Original ZIP/DB hashes, schema hash, 64 table hashes/counts and 331 complete main-table fixture rows |

The full DB hash catches any byte change. Logical hashes explain data drift independently of SQLite page ordering. Each table hash includes column names and rows sorted by their canonical JSON representation, preserving duplicates and NULLs. Serialization uses sorted object keys, UTF-8, compact separators and disallows nonfinite numbers. The fixture hash includes every column of every `status='final'` row ordered by integer ID; it is not limited to scorelines or league matches. Completed continental group fixtures, cup legs, world finals, their available events and all other historical records are additionally covered by full table hashes.

The schema fingerprint covers every `sqlite_master` object with SQL, ordered by type/name. SQLite's internal sequence table is excluded from user-table logical hashes, but remains protected by the full file hash. The baseline is packaged via `importlib.resources` so installed wheels retain audit protection.

The original audit performs SQLite integrity and declared foreign-key checks, checks schema/table inventory, then byte/logical preservation, independently derived league fixtures/standings, R25 event accounting, identities, competition inventory and budget limits. Read-only denial includes ATTACH and attempts to disable query-only mode. Connections close in `finally`. Canonical access remains read-only; Phase 1 introduces only isolated candidate writes as described below. No simulation module exists.

The baseline is deliberately specific to Save 046. An approved future checkpoint requires a new profile with explicit allowable administrative deltas, retention of completed-history checks and separate provenance. Phase 0 does not offer baseline recapture as a user command. Updating an expected digest is a history review, never a routine test fix.

Tests use disposable copies for every mutation, test denial against canonical read-only access and assert byte hashes remain unchanged. CI exercises Python 3.11–3.13 on Linux and Windows. No runtime network calls are needed; only installing development/build dependencies needs a package index.

The original nested backup chain remains preserved, not regenerated. Re-extraction into a fresh directory still restores the complete original handoff. Phase 1 additionally provides versioned candidate packages and independent parent/candidate restoration, described below.

## Phase 1 extension

`calendar.py` builds a dependency graph from existing brackets and all league commitments, then searches a deterministic hourly 16:00–21:00 grid backwards from a configurable 2027 year-end deadline. Constraint propagation preserves earlier-stage capacity; pairwise club conflicts, configured rest and rolling workload reject illegal new slots. Known ties retain their actual pairings; undrawn continental rounds reserve all potential qualifiers without generating outcomes. `validate_plan` independently scans the proposal and reports all rest intervals and inherited league exceptions. The solver establishes feasibility only within the modeled universe; foreign domestic calendars and actual itineraries are missing.

`payroll.py` calculates actual-day contract obligations in integer cents and enforces stable period identity, month-end cash timing, duplicate checks and reserve protection. `migrations.py` applies seven explicit administrative tables and eight authorized legacy-table deltas in one scratch SQLite transaction, with deterministic keyed before/after operations and exact DDL hash.

`profiles.py` retains the original 046 audit and adds a separate 046C profile. It authenticates the original parent and independently replays the pinned migration/plan in memory. Entire candidate schema and all 71 user-table contents must match that replay; 56 original tables must also retain their original baseline fingerprints. A rewritten manifest or operation log cannot authorize other changes. The plan JSON is packaged as trusted reviewed source alongside the untouched original baseline.

`checkpoints.py` authenticates parents, stages private copies, validates before atomic publication, exports reproducible manifest-backed ZIPs, verifies and restores into fresh directories, and separates candidate production from explicit acceptance. The promotion API requires exact parent/candidate hashes and all policy approvals, writes only a separate registry pointer, and has no Phase 1 CLI. It was exercised solely on temporary test registries. Default inspection still reads accepted Save 046.

The 046C candidate is conditionally calendar-feasible under 72h kickoff-to-kickoff including travel, three matches per rolling eight days and a December 31 deadline. It retains 12 fixed league rest shortfalls and proposes holiday/late-December rounds and long inter-leg gaps. A stricter extra-six-hour travel scenario has no solution in this conservative grid. These choices, unknown foreign calendars and the proposed payroll convention remain commissioner review items, not automatically accepted rules.
