# Candidate incremental payroll policy

Policy ID: `incremental_actual_days_month_end_v1`. This is an explicit **proposed** administrative convention for 046C, not a claim that the legacy simulation already used it. No tax, benefit, untracked base-roster salary or unapproved capital is invented.

Task 02B provisionally supports these accounting directions for preparing the revised candidate. This does not promote either save proposal. The v2 audit independently recalculates all September player-level due and accrued amounts and retains the evidence in its financial report.

The five recorded Vasco signing contracts establish R$310k/month (Gustavo Martins), R$430k (Villagra), R$640k (Carlos Vinícius), R$265k from September 1 (Arthur Dias), R$160k from September 2 (Barreal). The first three sum to the R$1.38m legacy monthly payroll and their contractual annual commitments reconcile with the unchanged wage budget. Transfers, contracts, ownership decisions, the R$13m supplemental fee authorization and ledger funding were inspected; none is rewritten.

January–July cash debits remain exactly as recorded. January's simplified full monthly charge and March's early posting are registered as `legacy_paid`, without retrospective reproration or date edits. They are historical evidence, not the new policy.

August has three full-month obligations totaling **R$1,380,000.00**. It is paid once on the unchanged checkpoint date **September 26**, tagged with obligation period **2027-08**. The booking date is not backdated to August 31 and is distinct from the covered period. Stable primary-key period registration and a unique ledger link prevent a second payment. Raw unregistered duplicate debits are rejected, including duplicates discovered after a period is already settled.

September is due at September 30 and **has no cash debit at this checkpoint**. Amounts accrue through September 26 inclusive. Use actual calendar days in the month, inclusive contract start/end, and round each player's obligation and accrued amount half-up to integer cents before summing:

| Contract | September covered days | Full-month obligation | Accrued through Sep26 |
|---|---:|---:|---:|
| Villagra | 30 | R$430,000.00 | R$372,666.67 |
| Arthur Dias | 30 | R$265,000.00 | R$229,666.67 |
| Barreal | 29 | R$154,666.67 | R$133,333.33 |
| Gustavo Martins | 30 | R$310,000.00 | R$268,666.67 |
| Carlos Vinícius | 30 | R$640,000.00 | R$554,666.67 |
| **Total** | | **R$1,799,666.67** | **R$1,559,000.01** |

The one-cent difference from rounding an aggregate is intentional under the per-obligation convention. The remainder between accrued and full-period obligation is a future September service commitment, not a cash expense already recognized. Paying later must first complete the period's accrual, then settle it once; early payment is rejected by the posting primitive. No such future payment or calendar advancement is performed here.

| Measure | Before | Candidate after |
|---|---:|---:|
| Restricted ledger cash | R$31,930,000.00 | R$30,550,000.00 |
| Recorded unpaid September incremental liability | Not recorded separately | R$1,559,000.01 |
| Cash less that recorded liability | Not reconciled | R$28,990,999.99 |
| Transfer-fee authority remaining | R$1,400,000.00 | unchanged |
| Annual incremental wage commitments | R$21,660,000.00 | unchanged |
| Annual incremental wage headroom | R$340,000.00 | unchanged |
| Agents/scouting headroom | R$2,190,000.00 | unchanged |
| Emergency reserve | R$16,000,000.00 | unchanged, ring-fenced |

Cash less this liability is an analytical subtotal, not newly approved acquisition capacity or a complete audited club balance sheet. Annual commitments are not charged to cash a second time. The payment primitive checks that a proposed debit leaves the restricted emergency reserve intact; no new capital is booked. Broader cash needs remain unknown because historical base payroll and other untracked liabilities are absent.

Commissioner decision: accept this actual-day, inclusive-date, month-end convention and the transparent August settlement, or request a revised candidate policy. Material alternatives include treating September joiners as full-month salaries, using a contractual fixed-day convention or different due dates; no evidence in the inherited data establishes those alternatives as already canonical.
