# September 30 first batch — unsigned review summary

**PLANNING ONLY. No official seed is committed, no decision is signed and nothing
is executed.** The [full unsigned template](first_official_batch_manifest.md)
contains the individual fixtures and complete configuration values.

Parent: exact accepted **Save 046C v2**, September 26, 2027 at 23:30.
DB SHA256: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`.
ZIP SHA256: `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`.

Proposed boundary: **September 30, 2027 at 23:59**.

| Commitment | Exact proposed scope |
|---|---|
| Libertadores | Eight R16 first legs, `lib:LIB-R16-01:L1` through `lib:LIB-R16-08:L1`. |
| Sudamericana | Eight playoff first legs, `sula:SULA-PO-01:L1` through `sula:SULA-PO-08:L1`. |
| Simultaneity | All 16 kick off September 30 at 16:00, from one common pre-kickoff state; deterministic persistence order. |
| Payroll | One `payroll:2027-09` obligation at 23:59, using `incremental_actual_days_month_end_v1`. |
| League | **Zero R26 fixtures.** Mirassol–Vasco, October 3 at 16:00, remains outside this batch. |

Recommended versions: `fictional-squads-1.0.0`, `braga-headless-1.1.0`,
`world-proposals-2.1.0`, `braga-knockout-2.1.0`,
`continuous-forward-lineage-2` and `career-stable-per-fixture-1`.
These remain subject to the [human policy review](commissioner_policy_review.md).

## Financial consequence if separately authorized

Read-only calculation from the existing five recorded signing contracts gives
September month-end incremental wages of **R$1,799,666.67**. Current ledger cash is
**R$30,550,000.00**; that single authorized debit would leave **R$28,750,333.33**.
The **R$16,000,000.00 reserve** and approved budget/annual commitment limits stay
unchanged. The accepted parent's accrued September liability is R$1,559,000.01;
it is part of the month-end obligation, not an additional cash debit. No September
payment has been posted by this task. Unrecorded base wages, match receipts,
awards and new capital are excluded.

## Distinct future decisions

1. Human reviews the policy bundle and explicitly permits protected production
   setup. No key, registry or career seed is provisioned during this task.
2. During that later setup, choose the career identity and commit its seed once,
   before any outcome. Preparation then binds the actual seed commitment,
   commissioner, exact parent, fixtures, payroll, configurations and manifest hash.
   The present placeholder is not an executable authorization.
3. Human authorizes that exact actual manifest with all seven required approval
   categories: rosters, historical unknowns, engine configuration, player timeline,
   competition rules/draws, financial restrictions and the specified batch.
4. Only the authorized trusted runtime may execute once and independently verify
   and restore the candidate. An interruption resumes its original commitments.
5. Human separately accepts the exact candidate, immediate-parent and package
   hashes using `accept_lineage_checkpoint`. An execution authorization does not
   supply this acceptance. October 3 then needs its own batch decision from that
   newly accepted parent, inheriting the same career seed.
