# Paired DEV checkpoint export benchmark

Export previously independently replayed the source, copied it, and independently
replayed the staging package again. The optimized path authenticates source
history/schema/signatures and pins its complete fingerprint, then fully replays
the copied staging package before atomic publication. The fingerprints/reports
must agree. Restoration still performs its own independent replay. No validation
result is cached and no history protection, package bound or production code is
removed. A new semantic-tampering regression proves authentic receipts with
divergent resulting state cannot publish a package.

`tools/benchmark_multiseason_export.py` ran sequentially on exactly the same
312-fixture TEST checkpoint using a public fixture key. It measured independent
validation, export, then independent restoration. The source files, all match
results, world fingerprint and every portable file were byte-identical before
and after. The source database was 124,461,056 bytes; the portable directory was
208,235,473 bytes. These are directory-package sizes, not compressed ZIP sizes.

| Measurement | Baseline | Optimized | Reduction |
| --- | ---: | ---: | ---: |
| Export wall time | 90.270 s | 47.967 s | 46.86% |
| Full verification/export/restore wall time | 176.754 s | 142.912 s | 19.15% |
| Full verification/export/restore CPU time | 162.422 s | 125.594 s | 22.67% |

This is one paired Windows/Python 3.12.14 sample. Caching and background activity
were not controlled, so it is not a statistical estimate or production/phone
episode latency claim. The workload packages an already simulated world; it is
not a complete forward-simulation batch timing. See
[complete measurements and hash comparisons](validation/continental_export_optimization.json).
The earlier 7.04% and 17.9% measurements concern different workloads and must not
be added to these percentages.

The DEV verifier still reconstructs all operations since migration. This change
does not implement independently verified immediate-parent incremental lineage,
history compaction or a production multi-season authority. Those remain separate
engineering gates. No installed worker or official artifact was changed.
