# Versioned checkpoint protocol, format 1

The permanent parent is authenticated against the original 046 SHA256 and complete Phase 0 audit. Only the explicit **046 → candidate 046C** migration is registered. The archive format, lineage metadata, atomic publisher, restore verifier and separate acceptance gate are reusable; future 047/048/2028 migrations need new registered validation profiles. Unknown versions and parent hashes fail closed. A future profile must retain the 046 baseline and protect settled sporting records across its allowed deltas.

Task 02B registers two explicit administrative revisions: immutable **v1** (calendar rejected, archival verification only) and default **v2** (`046_to_046C_admin_v2`, awaiting acceptance). V2 metadata names its revision and superseded proposal. The original DB/ZIP/profile are not overwritten. V1 promotion is blocked even when it passes archival integrity checks. The same schema version is sufficient because table definitions do not change; profile and plan identities distinguish authorized row deltas.

V2 adds 70 controlled future league kickoff adjustments, pins Mirassol–Vasco, preserves all 331 completed fixture rows and independently protects 55 entire original tables. It has 189 operation records and 378 complete keyed row changes including log rows. `finance.json` also contains player-level obligation evidence. All dates, manifests, hashes and reports are regenerated in a fresh output directory; no canonical promotion occurs.

## Lifecycle

1. `save create` authenticates the parent; reserves a sibling writer lock and creates a private staging directory. Both parent and working DB copies are isolated from the handoff.
2. `migrations.apply` runs explicit DDL and every administrative update inside one SQLite transaction, including provenance, monthly obligations and the operation log. Any failure rolls back the whole migration. Connections close before file publication/cleanup, including on Windows.
3. The 046C audit authenticates the preserved parent independently, reconstructs the authorized migration in an in-memory scratch database and compares the entire schema and every candidate table with that replay. It also checks original protected table fingerprints, standings, R25 accounting, identities, finance and the calendar model.
4. Reports and full-file manifest are written. Verification checks actual files/reports against the DB and profile, not a stored success flag. Only then is the directory published by rename. A failed staging run leaves no published checkpoint; interrupted runs may leave a sibling lock/staging artifact for explicit inspection.
5. Export creates a ZIP in a same-filesystem temporary file, verifies it by restoring into scratch, flushes it and publishes without replacing an existing file. Windows rename refuses existing files; POSIX uses an exclusive hard link. Restoration validates payload paths, sizes, duplicates, symlinks, CRCs, manifest, profile and reports before publishing a new directory.
6. Producing/restoring a candidate never updates the configured default database or a canonical pointer. The separate `promote_candidate` Python API requires exact approved candidate and expected-parent hashes plus all explicit policy approvals; it atomically writes only a JSON registry pointer under an exclusive lock and rejects conflicting heads. **No promotion CLI is provided or invoked in Phase 1.** Tests call this API only with temporary registries.

## Payload

| File | Purpose |
|---|---|
| `database.sqlite` | This checkpoint's database |
| `parent.sqlite` | Exact authenticated 046 parent (candidate packages only) |
| `checkpoint.json` | Format/save/schema/profile versions, parent and DB SHA256, unchanged fictional timestamp, candidate status, changed tables, operation count and required approvals |
| `manifest.json` | Sorted file names and SHA256 for every payload file except the manifest itself |
| `validation.json` | Actual validation findings; recomputed on verify/restore |
| `save046_baseline.json` | Permanent original historical baseline; equality with the installed baseline is verified |
| `operations.json` | Deterministic keyed before/after log: 119 records for v1, 189 for v2 |
| `changes.json` | Complete keyed row inventory including log rows: 238 for v1, 378 for v2 |
| `calendar_plan.json`, `calendar.json` | 57 actual-leg/reservation entries and independently checked feasibility/rest distribution |
| `finance.json` | Contract-based obligations, unique period payments, accrued liabilities and unchanged authority budgets |
| `report.md` | Full human-readable reconciliation, dates, finances, limitations and review decisions |

Original parent-only packages omit candidate-only files. Both revisions add the same seven administrative tables. V1 changes eight original administrative tables and retains the other 56 original table hashes. V2 additionally permits precisely 70 future fixture kickoff fields, retains 55 full original table hashes and separately proves that all 331 completed fixture rows remain unchanged. Player identities, transfers and associated historical records remain protected in both profiles.

Every operation ID hashes its table, primary key, complete before/after image and reason using the existing canonical JSON algorithm. The migration row hashes exact DDL. An operation log cannot recursively log itself; the complete `changes.json` inventory includes those own rows, while independent replay validates them. Calendar reservation rows identify potential qualifier sets without inventing winners, pairings or official undrawn match results.

ZIP timestamps are fixed at 1980-01-01, file order and permissions are fixed, and there are no real-time creation timestamps in migration data. Repeated builds and ZIP exports are byte-identical in the tested Python/SQLite/zlib runtime. Across runtime/compression versions, semantic identity and file-level hashes remain verifiable, but identical compressed ZIP/SQLite layout bytes are not promised; retain the produced archive's actual SHA256.

## Storage and restoration

`output/` is ignored; no generated DB or accumulating backup ZIP is committed. Keep the single original handoff ZIP already in Git unchanged. Store accepted checkpoint packages in user-controlled backup storage or deliberately published GitHub Release assets, with an independent SHA256 inventory, immutable filenames, at least two copies and periodic restore tests. Upload/release publication has not been performed by this task. Avoid endlessly nesting every prior ZIP in each new archive: store parent hashes and retain the immutable parent package externally; 046C includes the exact 046 database so the first parent can be restored independently.

Manifests detect corruption, not authorship: they are not signatures. Re-sealing an altered manifest cannot authorize a history change because registered profiles replay the approved delta against an authenticated parent. Python package/profile code is a trusted review surface; a future accepted checkpoint needs a registered, reviewed profile, not an edited digest to silence tests. Restore never executes archive code.

No crash-durability claim is made for cloud sync or sudden power loss beyond SQLite transaction semantics and flushed atomic file publication on the host filesystem. Exclusive locks coordinate this application's writers. Stale locks after a crash should be investigated, not automatically bypassed. The policy choices listed in candidate metadata remain commissioner decisions before any real acceptance.
