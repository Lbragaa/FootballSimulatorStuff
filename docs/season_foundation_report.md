# Multi-season foundation report

This delivers the requested discovery/planning stage and first independently
testable foundation, on `codex/multiseason-foundation`. It does **not** deliver a
playable 2028 season or change production runtime 0.12.0.

## Delivered

* [Architecture, competition inventory, policy proposals, migration design and
  ordered milestones](season_2028_implementation_plan.md).
* [Observed episode timings, controlled pipeline profile and optimization
  strategy](performance_optimization_plan.md), with
  [safe numerical evidence](validation/multiseason_baseline.json).
* `braga_era.seasons`: accepted-parent adapters, isolated immutable-parent
  rehearsals, explicit closure/policy checks, atomic lifecycle journal, archive
  references, concurrent exact retries and independent journal reconstruction.
* Pure versioned double-round-robin drafts: 380 fixtures/38 rounds/19 home and
  away for 20 clubs, tested for 2028, 2029 and 2030. No dates/entrants invented.
* `tools/profile_pipeline.py`: fixed-seed DEV execution/export/independent restore,
  stage CPU/wall timings, bounded safe profiler output and restored-state equality.

The complete available parent DB is retained as the archive; unknown legacy
awards/statistics/coaching observations are not manufactured. Season/year labels
remain separate from dates. Cross-year pending commitments stay in the snapshot
and archive manifest rather than being cancelled. Workflow transitions stop at
offseason_preparation until generators/economics/registration validation exist.

## Evidence

The current registered parent was authenticated locally, and a new nonpromotable
rehearsal was made from its exact database. Its season closure correctly fails
for unfinished required competitions and administrative obligations. Registry,
key, config and standing-delegation hashes were unchanged by that operation. No
worker transport, match execution, authority provisioning or acceptance was used.

The fixed-seed root DEV baseline independently restored the same semantic state
after 16 fixtures. Instrumented stage wall times: initialization 6.713s,
simulation/audits 32.435s, export/validation 114.640s, extra restoration 50.900s.
The profile identifies repeated canonical serialization and table fingerprinting
as meaningful investigation targets. No production speedup is claimed.

Final focused compatibility run: **70 passed**, including all **22 new season
tests**, historical projection/bridge reads, episode presentation/recovery and
protocol grammar. Separate corrected-cache authority/bridge/season run:
**57 passed**. Rehearsal cases include missing/pending records, unknown scores,
unscoped competitions, unresolved claims, cross-year dates/pending identities,
corruption, duplicate requests, concurrent runners, crash before/after commit,
portable archive inspection, and refusal of unsupported policy or activation.

The complete local sweep reported **386 passed, 2 skipped, 10 setup errors** in
878.72 seconds. All ten errors came from selecting the old
`output/task03d-chain-final` cache, whose report lacks `registry`; the two skipped
bridge tests also need its missing portable bundle. With
`BRAGA_LINEAGE_TEST_CHAIN=output/task03d-final`, the separate 57-test run passed
the complete authority/bridge/season selection, including every affected case
and both skipped bridge tests. The final 70-test run used that corrected fixture
too. This was an invocation/cache error, not a weakened test or regenerated
baseline; there is no claim of a single uninterrupted all-green full run.

Foundation checks also passed: handoff authentication, read-only root inspection
and root audit (36 passes, no failures, ten documented inherited warnings).
These inspect the installed historical root, not the current production clock.
No test/baseline was removed or weakened. Windows/Python 3.12.14 was tested locally;
the existing six-platform/version CI remains a separate verification gate.

## Boundaries and next work

No football/seed/engine/lineage/bridge implementation was changed. The installed
worker, startup, private README, secrets, career files and bridge sequence were
not deployed or reset. No official transition, official simulation or new
accepted checkpoint was produced by development.

Next engineering is the reviewed edition-scoped migration/profile, legitimate
promotion evidence/process and competition/calendar generators. Performance
optimization can proceed in parallel using the measured baseline. Commissioner
decisions on tournament scope, promotions, allocations, economic inputs and
new-profile authority are still required before official activation. Full-year
2028 and 2029 replay/stress evidence is **not available yet**; this report makes
no multi-season readiness claim.
