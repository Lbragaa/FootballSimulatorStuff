# Phase 0 architecture

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

Audit performs SQLite integrity and declared foreign-key checks, checks schema/table inventory, then byte/logical preservation, independently derived league fixtures/standings, R25 event accounting, identities, competition inventory and budget limits. Read-only denial includes ATTACH and attempts to disable query-only mode. Connections close in `finally`. No writable application connection, repair command or simulation module exists.

The baseline is deliberately specific to Save 046. An approved future checkpoint requires a new profile with explicit allowable administrative deltas, retention of completed-history checks and separate provenance. Phase 0 does not offer baseline recapture as a user command. Updating an expected digest is a history review, never a routine test fix.

Tests use disposable copies for every mutation, test denial against canonical read-only access and assert byte hashes remain unchanged. CI exercises Python 3.11–3.13 on Linux and Windows. No runtime network calls are needed; only installing development/build dependencies needs a package index.

Backup restoration today means extracting the authenticated original handoff again into a fresh directory (`--destination`) and running both verifiers. Versioned writable save creation, transactional validation/promotion and restoration management are future milestones; the original nested chain remains preserved, not regenerated.
