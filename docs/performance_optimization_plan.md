# Verified-pipeline performance plan

## Measured starting point

On 2026-10-29 a read-only extraction of 17 existing durable episode timing records
confirmed that local processing is the dominant user-visible delay. This read
did not execute a command, consume a page, accept a save or change the registry.
Only aggregate timings are published; private journals stay local.

| Category | Samples | Min seconds | Median seconds | Max seconds |
| --- | ---: | ---: | ---: | ---: |
| Whole episode | 17 | 42.917 | 324.761 | 1088.930 |
| Manifest preparation | 13 | 0.641 | 3.266 | 7.473 |
| Simulation and export | 13 | 45.620 | 145.041 | 308.146 |
| Independent verification/restoration | 13 | 41.540 | 107.263 | 269.150 |
| Acceptance | 13 | 13.867 | 39.180 | 170.666 |
| Narration | 17 | 17.642 | 43.140 | 224.439 |

These are heterogeneous episodes with 0–several batches, not a controlled A/B
benchmark. Stage sums do not explain all episode time: state reads, complete
fingerprints, durable journal writes and other coordinator work are outside
those category timers. Do not sum medians or report them as speedup evidence.
GitHub polling/posting time is separate from these local measurements.

## Reproducible disconnected baseline

`tools/profile_pipeline.py` accepts only exact released accepted-root bytes,
creates a fresh explicitly nonpromotable DEV world and uses one fixed committed
seed. It simulates the first simultaneous continental group, exports with all
existing validation, restores independently and compares every semantic table
fingerprint. It never reads a production key, config or registry or creates a
GitHub transport. No scores are printed or included in benchmark JSON. Private
world/archive files contain noncanonical results and stay under ignored output.

```powershell
.\.venv\Scripts\python.exe tools/profile_pipeline.py `
  --db output/Save046C_v2/database.sqlite `
  --output output/multiseason-profile-FRESH
```

The directory must be new. `benchmark.json` includes stage wall/CPU time,
SQLite connection-execute call counts by category/stage, top application
functions by cumulative/self time, peak traced Python allocation, DB/archive
sizes, unchanged input hash and independent-restoration equivalence. Temporary
verification directories are confined to the benchmark tree; process-wide
instrumentation is restored on failure. No SQL text, result JSON or secrets are
included. `cProfile`/`tracemalloc` overhead is material; these instrumented times
are not ordinary worker latency. Direct cursor calls and engine OS-level memory/
disk counters are not yet measured. Independent restore runs the original
verification; no replay flag is disabled.

Measured Windows/Python 3.12.14 instrumented run (16 fixtures; fixed seed;
exact root preserved; restored semantic hash identical):

| Stage | Wall seconds | CPU seconds |
| --- | ---: | ---: |
| Initialization | 6.713 | 6.688 |
| First simultaneous group, including audits | 32.435 | 31.719 |
| Export including independent validation | 114.640 | 113.578 |
| Additional independent restoration | 50.900 | 50.516 |

The profile recorded 206,845 SELECT execute calls, 3,067,383 canonical JSON
calls (116.192 cumulative seconds), 3,621 table fingerprints (74.376 cumulative
seconds), and 20 world audits (99.619 cumulative seconds). Export dominates this
controlled workload; it includes directory validation, archive verification and
their required replays. Cumulative function times overlap and must not be added.
This supports investigating repeated serialization/fingerprints and immutable
state reads before adding parallel match execution. It does not establish that
any verification can be removed. Sizes, memory and exact aggregate query counts
are recorded in the committed safe [baseline evidence](validation/multiseason_baseline.json).

The initial attempt encountered the sandbox's inaccessible system TEMP during
archive verification. The profiler now gives nested standard-library temporary
operations an explicit owned development directory; it does not alter engine
publication or weaken validation. An occasional OneDrive rename denial also
affected a test run; rerun fixtures outside OneDrive rather than changing the
atomic publisher or expected hashes.

## Hotspot hypotheses to measure

Source inspection shows several costly operations, but inspection alone is not
evidence of their relative CPU cost:

1. `lineage.parent_info` authenticates packages/support and recomputes full semantic
   fingerprints. `Episode.state`, previews, narration pages and reports may
   repeatedly authenticate the same immutable accepted payload.
2. `verify_payload` checks history/schema/journal/state and replays only the newly
   authorized delta. This is **already incremental by accepted parent**. Proposing
   delta replay as though it were missing would duplicate existing functionality.
3. Export verifies a directory, constructs ZIP bytes and independently restores
   them. Candidate inspection and acceptance validate the resulting artifact
   again. These checks have distinct trust purposes; avoid removing one merely
   because another also calls audit.
4. `history.table_fingerprint` serializes and sorts every table's rows. Large
   immutable event/blob/journal tables grow across the season; `storage.captured`
   and full before/after journal comparison also revisit large inventories.
5. Player-team construction queries per-player state/discipline and source
   historical appearances. Measure N+1 SELECTs before batching them.
6. Narration can load/validate the same result for many pages; episode baseline,
   historical projection and table recalculation can repeat the same source scan.

## Optimization order and trust constraints

First benchmark a bounded disconnected current-parent episode with the existing
rehearsal harness and finer observer timers (no transport, no key copied, no
authority provisioned). Record cold/warm runs, exact start/end logical hashes,
fixture count, bytes and hardware/Python/storage environment. Treat its signed
clone as PRIVATE NONCANONICAL and never copy it back. Capture query plans for
fixed internal SQL and aggregate categories; never output expanded parameterized
SQL containing world data. Measure CPU vs wall time, disk bytes and compression
separately, then compare the root DEV baseline with the growing lineage workload.

Priority candidates after profiling:

* Request-local reuse of already validated immutable input/result objects. Bind
  caches to exact file/content hashes, policy/profile and authenticated accepted
  parent; clear at acceptance. Never trust mtime alone or cache successful
  verification across an unverified write or changed authority/cursor revision.
  Mutable SQLite sessions and WAL/journal-backed inputs are not immutable cache
  entries; authenticate their complete logical state through the existing path.
* Batch read-only state/discipline/appearance loading, retaining chronological
  ordering, NULL/unknown semantics, identity exclusions and simultaneous inputs.
* Reuse one in-memory results projection per exact request/snapshot/visibility.
  No shared mutable narration cursor cache; retries still return committed pages.
* Profile canonical serialization and reuse proven byte values inside a single
  operation. Any fingerprint optimization must be bit-for-bit equivalent for
  every table, NULL, Unicode and row ordering, including malformed inputs.
* Compression tuning or avoiding redundant temporary copies only after measuring
  archive construction cost. New byte layouts cannot replace old accepted ZIPs;
  new packages still require complete manifests, safe extraction and independent
  replay/restoration before acceptance.
* Indexes belong only in a registered new forward schema, not silently in old
  accepted databases. Validate query plans and deterministic record application.
* Parallel pure simulations are lower priority: pre-kickoff snapshots and seeds
  are committed first, outputs validated independently and applied in stable
  order. SQLite writers/acceptance/claims remain serialized.

Never cache a bare success flag, accept before verification, reseed a slow match,
change event ordering or retrospectively rebuild accepted packages. Profile 2's
full history guard and frozen baseline checksums stay strict. Any broader
incremental-validation contract needs a new reviewed profile and independent
adversarial validation, not a shortcut in the installed worker.

## Performance gates

For each optimization: use identical starting parent, policy/config and fixed
fixture commitments; compare events/results, table fingerprints, finances,
operation logs, narration ordering/visibility and independent restored state.
Inject interruption before/after each commitment/acceptance/page/post; same UUID
must yield original output. Record absolute times and ratios on repeated runs,
plus CPU/memory/I/O and package-size changes. Test Windows/Linux Python 3.11–3.13
in CI before deployment. Target multi-fold improvements where supported by data;
no gain is claimed by this first foundation milestone. Production worker 0.12.0
and its credentials/task/delegation remain untouched.
