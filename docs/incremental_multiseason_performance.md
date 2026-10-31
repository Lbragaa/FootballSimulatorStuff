# Immediate-parent development verification

The subsequent [offseason integration](offseason_integration_report.md) measured
a separate payroll query optimization on identical all-club inputs: 23,322
SELECTs versus six, with byte-equivalent cent totals. That is not a rolling
checkpoint lifecycle or phone episode benchmark. The limitations below remain.

`DEV-MULTISEASON-INCREMENTAL-1` is a separate, nonpromotable TEST profile. Existing
full-history verification/export behavior and production profiles are unchanged.

The verifier first independently restores and fully replays a normal DEV parent.
It signs an attestation binding exact snapshot bytes, world hash, operation count,
operation head and verifier version. A child keeps the same migration/root/seed
and exact inherited operation prefix. Validation authenticates that parent,
independently replays every suffix operation from its snapshot, then compares
**all** tables, including historical records. Changed parent bytes, signatures,
prefixes, child history, unsupported profiles and extra files fail closed.
Packages never contain signing keys. Export and restore publish atomically.

This explicitly changes the verification trust boundary: the signed full-parent
attestation substitutes for resimulating all ancestors at each restore. A trusted
key holder can forge an attestation. It is not distributed consensus, an official
registered successor profile, or an approved production history-compaction scheme.
Production registry fencing, authority integration and interrupted-export recovery
still require separate engineering/review. Old full replay remains available.

## Identical-input Windows / Python 3.12 measurement

The baseline is the 549-operation world after the shared 2028 season and 48
2029 fixtures. The immediate parent has 527 operations; the child independently
replays the original **22 operations with identical UUIDs, arguments and responses**.
Both verifiers produced world SHA256
`b73395d6702474667ccd3ac106ca075a45d16d432a637f29684c0bd8cb9916dd`.
All source files stayed unchanged. Exact retry returned the original response.

| Measurement | Wall seconds | CPU seconds |
| --- | ---: | ---: |
| Full-history validation, 549 operations | 171.980 | 138.016 |
| Immediate-parent validation, 22 suffix operations | 85.655 | 20.703 |
| One-time full parent replay/sealing | 137.698 | 129.047 |
| Child creation/authentication | 18.129 | 16.344 |
| Apply original committed suffix | 17.625 | 16.422 |
| Incremental export | 40.858 | 28.500 |
| Independent incremental restoration | 42.843 | 21.156 |

Paired validation wall reduction: **50.19%**; CPU reduction: **85.00%**. This is
one sequential sample with uncontrolled cache/background activity. Initial seal
cost is separate. It is not a full-pipeline paired improvement or measured phone
episode latency. Earlier 7.04%, 17.9% and 19.15% results cover different workloads
and cannot be added to it.

For a single new parent/child pair, sealing plus suffix validation costs more
than the measured full-history validation alone. The current prototype seals
normal DEV packages; it does not yet cheaply roll a verified child into the next
trusted parent. That rolling attestation/registered-chain work is still required
before claiming a continuous-career latency improvement. The result establishes
suffix verification equivalence and its isolated cost, not a cheaper complete
successor lifecycle.

Storage is a real tradeoff: sealed parent 315,997,354 bytes; incremental portable
directory 644,750,518 bytes. These are uncompressed directories, not ZIP sizes.
The profile duplicates snapshots and is **not** a package-growth optimization.
Observed normal-profile growth was 83,759,104 database bytes at completed 2027,
232,222,720 after the 1,341-match 2028 world, and 244,977,664 after 48 more 2029
matches. Normal portable directories were 315,997,152 and 328,752,096 bytes at
those last two boundaries. Full 2029 storage and multi-year compaction were not
measured or implemented.
Aggregate process peak resident memory was 567,762,944 bytes; it is not a
per-phase measurement. More seasons and repeated statistical samples remain
needed to establish scalability.

[Complete safe measurements](validation/incremental_multiseason_benchmark.json).
Reproduce with disconnected test packages only:

```sh
python -m tools.benchmark_incremental_multiseason --parent-package output/shared-2028/portable --child output/shared-2029/world --output output/incremental-2029
```

Six dedicated regressions passed: concurrent exact retry and crash after commit,
full-replay equivalence, export/restoration, malformed inventory, and parent,
signature, history, prefix and extra-file tampering. No football outcome, event
ordering or seed policy was changed for performance.
