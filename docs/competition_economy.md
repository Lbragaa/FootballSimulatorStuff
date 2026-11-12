# Competition economy for the 2029 candidate

`competition-prizes-brl-1` is a fictional BRL award schedule. CONMEBOL’s
2024 budget distinguishes preliminary phases, group participation, group
wins, advancement and exclusive final awards. The CBF’s 2024 Copa do Brasil
report distinguishes the title payout from cumulative competition receipts.
Those references informed the structure. The amounts below are deliberately
scaled for the existing simulated ledger. They are neither currency conversions
nor claims about Brazilian broadcast contracts or the real 2029 season.
[CONMEBOL financial report](https://cdn.conmebol.com/wp-content/uploads/2025/04/CONMEBOL_INFORME_FINANZAS_2023-ESP-DIGITAL.pdf)
[CBF Copa do Brasil report](https://www.cbf.com.br/futebol-brasileiro/noticias/detalhes/competicoes-copa-brasil-masculino/flamengo-e-campeao-da-copa-betano-do-brasil)

| Rank | Série A (BRL) | Série B (BRL) |
| ---: | ---: | ---: |
| 1 | 8,000,000 | 2,200,000 |
| 2 | 6,500,000 | 1,800,000 |
| 3 | 5,500,000 | 1,500,000 |
| 4 | 4,800,000 | 1,300,000 |
| 5 | 4,200,000 | 1,150,000 |
| 6 | 3,700,000 | 1,050,000 |
| 7 | 3,300,000 | 950,000 |
| 8 | 2,950,000 | 850,000 |
| 9 | 2,650,000 | 775,000 |
| 10 | 2,400,000 | 700,000 |
| 11 | 2,200,000 | 650,000 |
| 12 | 2,000,000 | 600,000 |
| 13 | 1,850,000 | 560,000 |
| 14 | 1,700,000 | 520,000 |
| 15 | 1,550,000 | 480,000 |
| 16 | 1,400,000 | 450,000 |
| 17 | 1,200,000 | 420,000 |
| 18 | 1,100,000 | 390,000 |
| 19 | 1,000,000 | 360,000 |
| 20 | 900,000 | 330,000 |

| Competition | Cumulative entry / progress awards (BRL per club) | Exclusive winner / runner-up (BRL) |
| --- | --- | --- |
| Libertadores | Preliminary 1/2/3 220,000 / 320,000 / 470,000. Group 2,100,000. Each group win 230,000. R16 1,400,000, QF 2,200,000, SF 3,200,000. | 14,000,000 / 6,400,000 |
| Sudamericana | Preliminary 180,000, group 850,000, each group win 90,000, playoff 450,000, R16 700,000, QF 1,100,000, SF 1,600,000. | 6,800,000 / 3,100,000 |
| Copa do Brasil | R1–R4 150,000 / 200,000 / 300,000 / 450,000. R32 650,000, R16 950,000, QF 1,500,000, SF 2,400,000. | 8,500,000 / 4,200,000 |
| Carioca | Pool 120,000, QF 180,000, SF 300,000. | 1,250,000 / 650,000 |
| Supercopa | — | 1,800,000 / 950,000 |
| Recopa | — | 2,400,000 / 1,150,000 |
| Other state, regional, access and lower-division competitions | R$0 under this version. | — |

Participation counts once per played stage, regardless of the number of legs.
Direct entrants receive only the rounds they play. Group win awards use final
group scores. A cross-competition entrant earns the stages it actually plays.
The final pays either the winner or runner-up amount. There is no separate
cash award for securing next-season qualification.

## Settlement and Vasco preview

The signed transition settles the archived prior season on January 1 after
opening budgets and before autonomous recruitment. The existing operation
journal and stable ledger IDs prevent double payment. Old award-shaped ledger
entries that cannot be reconciled block settlement. This policy allocates 30%
to additional fee authority and 10% to additional annual wage authority and
wage cap. The remaining 60% adds no new market authority. The entire receipt
is cash, and spending still requires adequate cash after reserves and liabilities.
The same percentages apply across clubs. Receiving an award does not guarantee
a transfer or an agreement. Future seasons settle through the same signed
boundary, without January awards being backdated to the archived season.

Read-only provisional calculation from accepted head
`b2bca858a705aec186638df0cf1967c4ceb0fd79c7aae109febe240070fbd2a1`.

| Vasco earnings | BRL |
| --- | ---: |
| Série A, fourth | 4,800,000 |
| Libertadores preliminary rounds 2 and 3 | 790,000 |
| Libertadores group participation and three wins | 2,790,000 |
| Libertadores R16 and QF | 3,600,000 |
| Copa do Brasil R32 | 650,000 |
| Carioca pool, QF and SF | 600,000 |
| **Total** | **13,230,000** |

| Account column | Observed | Prize-only projection (BRL) |
| --- | ---: | ---: |
| Cash | 40,539,275.90 | 53,769,275.90 |
| Protected reserve | 16,000,000.00 | 16,000,000.00 |
| Fee authority | 1,054,672.12 | 5,023,672.12 |
| Additional annual wage authority | 106,413.76 | 1,429,413.76 |

The head is not archived. These projections isolate the award from the
remaining 2028 payments, January economics and subsequent transfer spending.
The snapshot includes R$54,890,118.00 of modeled operating income, no verified
sponsorship contracts, and R$9,732.76 in pending conditional performance bonus
entries. Annualized active contracts total R$36,332,618.88 at that head,
before loan share and expiry adjustments. `current_finances` reports the new
itemization, outstanding recorded obligations and the cash buffer after the
policy is adopted.

## Market

The prior auction used an ability-only fee, one agreement threshold and a
sporting shortlist score for bid precedence. With the new settlement in place,
the January auction calculates modeled asks from age, remaining contract,
position, positional depth, recent ratings weighted by minutes, current injury,
seller liquidity and recent continental entry. Age and ability serve as a
potential proxy. The model has no reliable career-wide injury-frequency or
observed market-value data. Its figures are asking prices, not estimates of
real-world transfer fees.

Under the new policy the most important players command a premium, are more
likely to stay and are excluded from ordinary loan bidding. Offers compete
by transaction type, fee and wage before the existing recruitment score.
Borrowing requires an owner’s contract that spans the loan. Reserved cash,
installments, annual caps, registration and the existing ownership paths still
apply. Managers remain autonomous. The upgrade does not introduce a human
transfer command, discretionary counteroffer UI, or summer window.

For Hikari, start with `career_statistics` using `dataset: squad`, then
`current_finances`, then `career_statistics` with
`{"dataset":"transfer_market","club":"club:15","season":2029,"limit":30}`.
This shows the recorded squad needs, shortlist offers, salary expectations
and refusals. Use `dataset: transfers` for executed transactions. Journal
offers are historical terms, with no implication that they are still open.
Any manual offer, sale or loan should require
an explicit separate mode and exact signed terms bound to the accepted parent.
Ordinary gameplay should never imply approval of a user-directed transfer.
