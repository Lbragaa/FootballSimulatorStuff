# Autonomous offseason integration — development only

This milestone adds working offseason execution to the established shared season,
not another match engine or production transport. PR #11 still depends on open
PR #10 (`7aedb4bc18f95026de831a56d9a9fad21b04e606`). No production registry,
accepted career, key, installed worker, delegation or official match was accessed
or changed. **This is not approval or readiness for official 2028 activation.**

## Implemented mechanics

`autonomous-offseason-development-1` is an explicit opt-in extension. The signed
`install_offseason` operation installs migration 2; migration 1 and its frozen DDL
remain unchanged. Validation checks the exact additional table/index inventory,
migration hashes, signed installation receipt, complete operation chain, protected
history and independent full replay. Existing worlds without the extension retain
their previous behavior.

The model plans every supported club from a shared scouting snapshot. Position
depth, quality, club strength, developing/contending strategy, age priors and
financial capacity influence offers. Two first-choice bids per club compete for
players; named player/club/season streams decide agreement/refusal. Ownership
changes only once per winning agreement. Luan Braga remains Vasco's autonomous
manager, with no preferential football random stream.

Purchases/sales, free agents, expiring contracts, same-wage renewals, releases of
expired/non-guaranteed terms, loans and returns persist in existing contract,
transfer and loan records. Committed loan purchase options have a separately
tested execution command. Fees have 30% upfront/70% July installments; agent cost
is 4%, signing bonus one monthly wage, and a contingent half-month bonus requires
ten actual appearances for the buying club in that season. Installments are
reserved as liabilities, not counted as spendable future receipts. Agent costs
and signing bonuses debit immediately; transfer payments credit the seller only
when actually paid. Existing guaranteed wages cannot be released without an
additional compensation policy.

Registration is recorded and reconciled against actual ownership, including loan
returns. The proposed windows are January/February and July. The offseason is a
bounded January 1 clearing session, not daily negotiations throughout all those
months. A registration contingency may negotiate with up to ten *other* available
free agents, at most three acquisitions, when a club has fewer than 18 players
or two goalkeepers. It cannot retry a previously submitted/refused offer, invent
an emergency player or bypass budgets. Failure remains an explicit blocker.

Annual development/decline uses explicit modeled ages when birth dates are absent;
no historical birthday is manufactured. The new policy has bounded +/-2 attribute
observations, independently versioned from the frozen generic +/-1.5 evolution.
It respects known potential caps. Retirement, two fictional academy arrivals per
club/year, persistent collision-checked identities, medical/disciplinary state,
historical snapshots and native archived identities are preserved. Retired
players cannot become available merely because their contract expires.

## Financial assumptions and boundaries

Every club's scenario is an immutable signed input with explicit provenance.
Unknown opening wealth is excluded from recognized cash. Initial 2028 hypothetical
liquidity for other clubs is separately posted as TEST-only modeled money; it
cannot recur in 2029. Vasco receives **no opening capital or reset fee/wage
authority**, and its recorded reserve remains protected. A failed payment or wage
plan rolls back; there is no insolvency bailout.

Unknown wages and operating revenue/costs are prospective scenario assumptions.
Wage/valuation formulas depend on quality; all amounts, including foreign-club
economics, use fictional BRL units. Known contract wages remain exact. The helper
models monthly income from the explicit projected wage base and recurring cost;
it does not claim a sponsorship, competition prize, missing historical revenue,
known debt maturity or commissioner authorization. The prior R$3m/month scenario
is not treated as approved revenue. Recorded financial history/debt constraints
are not rewritten; unknown base debt and commercial contracts remain unknown.

These scenarios deliberately allow a funded development stress test. They are
not calibrated all-club accounts: income is comparatively stable, realistic
commercial shocks/currencies/prize schedules are not modeled, and future official
budgets need an explicit approved policy. Purchase options are available/tested,
but autonomous option exercise and richer counteroffer bargaining remain work.

## Verified integration

The completed NONCANONICAL 2027 source was authenticated and archived by the
existing migration before the new January session. One persistent 2028 world
then ran all **1,341 established fixtures / 14 editions with updated squads**.
No scores were injected. Shared rest/calendar, standings and finance checks,
full replay, portable export and independent restoration passed:

| 2028 outcome | Recorded count |
| --- | ---: |
| Clubs planned (all registered world clubs) | 285 |
| Players developed | 7,230 |
| Forward retirements | 111 |
| Fictional youth intake | 570 |
| Purchases / loans | 63 / 15 |
| Rejected offers / submitted offers | 70 / 570 |
| Releases | 27 |
| Loan returns | 15 |
| Paid fee installments | 78 |
| Actual triggered performance bonuses | 16 |
| Payroll periods reconciled | 12 |

All 285 cash accounts reconcile to their recognized openings and ledger; no
pending 2028 economic obligation or mismatched final club registration remains.
The resulting TEST world has 544 operations and SHA256
`a9029c0fa2e89896ba5f3c99257128c1417739b04b39d4406318e6d92c0fc93d`.
New outcomes differ from the prior season test because squads changed, as intended.
The original no-offseason 1,341-match world independently replays to its original
`e1b0056c457106bb7728e801068f7bd1bf4fafbb01fb4f8b75ee6ad34573f1ec`;
the earlier 312-match world still has
`f4664a5c222af8576b8f582befc27269ab5e300f675a4efab94b35bb5eb72fef`.

Testing found a real shared-time loan-return UUID collision. Return commitments
now include the loan identity; recovery reused original requests, seeds and
cached fixtures. Comparison confirmed **778 existing development match inputs,
seed commitments and results were unchanged**, rather than rerolled.

The second January session has executed on the inherited world: 285 clubs,
7,665 developments, 135 retirements, 570 youth arrivals, 93 purchases and three
loans. Nine purchases were free-agent signings, with 3,913 expirations and 5,835
renewals. Forty-eight actual 2029 league fixtures were persisted with recorded
division movement. Full independent replay, portable export and restoration
passed: **566 operations**, world SHA256
`e3727f533da284e6ea76f1d9b1be70b7132bafbe950e030105d24d6425861366`.
All inherited 2028 scores/receipts and the source package stayed unchanged.
The runner's final file-preservation check initially failed because a local
configuration variable shadowed its checksum dictionary; separate variable
names repaired that check. Neither package was resealed or altered to pass it.
A complete 2029 continental/state/cup season is **not** claimed.

[Safe counts, hashes and reconciliation](validation/offseason_integration.json)
contain no match scores or private signing material. The database grew from
303,788,032 bytes after 2028 to 338,612,224 after the second offseason and 48
2029 fixtures. Normal directory packages grew from 387,562,453 to 422,386,645
bytes. No compaction or rolling-authority storage reduction is claimed.

## Verification, performance and CI

Local evidence: seven offseason regressions passed (104.76s), 56 combined
market/calendar/history regressions passed (682.63s), and 30 episode/protocol
compatibility checks passed (6.18s). The seven cases include crash-after-commit,
concurrent exact retry, portability, capital refusal, insolvency rollback,
duplicate payroll, same-time loan returns, purchase options, guaranteed wages and
retirement/expiry exclusion. Some suites overlap; these are not additive totals.

Paired identical-input payroll processing produced identical cents/hash. Across
three months, the old per-contract query strategy used 23,322 SELECTs versus six
for a single invocation-scoped loan-table load. Wall time was 1.1719s versus
1.0326s (~11.9%). This is a single payroll benchmark, not an episode or full
successor-lifecycle speedup. Independent verification still recomputes everything.
The resumed 2028 process recorded 720.0s including remaining agenda, verification,
export and restoration; this excludes earlier interrupted work and is **not**
comparable end-to-end timing to the previous 651s rehearsal.

CI run 83 completed five jobs successfully, including the repaired draw and
shared-calendar workload on Linux 3.12. Linux 3.13 failed after exhausting its
disposable-file quota, not because a failed assertion was suppressed. CI now
cleans only validated pytest-owned copies, removes the fixed CI test directory
after pytest exits, and retains XML/source/rehearsal evidence.
New-head Windows/Linux Python 3.11–3.13 verification is required before merge.

## Reproduce and remaining activation blockers

```sh
python -m tools.rehearse_domestic_season --db output/ci-season/database.sqlite --output output/offseason-2028 --continental --offseason
python -m tools.rehearse_domestic_transition --package output/offseason-2028/portable --output output/offseason-2029 --offseason
python -m tools.benchmark_offseason_payroll --db output/offseason-2028/world/database.sqlite --output output/payroll-comparison.json
```

Use only authenticated completed NONCANONICAL sources and separate test outputs.
Retries consume the original economic configuration, not recomputed inputs from
an already advanced world. No production installer or bridge binding is invoked.

Still required: full non-RJ state/federation qualification, financial/age/market
calibration and commissioner decisions, compensation for releasing guaranteed
contracts, richer market cycles, full 2029 competition repetition, season-aware
production lineage/authority and signed phone episodes. Rolling attestations and
multi-successor storage/performance improvements were deliberately not spread
into partial implementations here. The existing sealing/duplication limitations
in `incremental_multiseason_performance.md` remain. No standing 2027 gameplay grant
authorizes these new policies or a season activation.
