# Verified canonical history and provenance

Current checkpoint: Task 03A accepted **046C v2** administratively, database SHA256 `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`, ZIP `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`. The date and all settled sporting history below remain unchanged. August payroll, objectives and approved future calendar adjustments are described in [Task 03A](task03a_report.md). The remainder of this document records the preserved original Save 046, including its original cash and calendar defects; it is not a new 046C financial statement.

Source: the repository's original `BRAGA_ERA_HANDOFF_AFTER_046.zip`, safely reproduced into `data/handoff/`. Its full internal SHA256 manifest was validated. The unmodified original verification script passed, including equality of the extracted database with `Save046/braga_save.sqlite` inside the original nested Save046 ZIP. Reference engines were inspected as text only.

| Artifact | SHA256 |
|---|---|
| Original handoff ZIP | `527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719` |
| Canonical database | `de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28` |
| Logical completed-fixture snapshot | `edb9ae71410c83c6c2c09a501af6022cf2263a8901bd1faa7dba03e4068ff639` |

The database is Save **046**, fictional **2027-09-26 23:30**, with board confidence **61/100** and `braga_matches=45`. Dates describe fictional local event time, independent of the host clock.

The 2027 Brasileirão has **20 participants**, **380 fixtures**, **250 final** (R01–R25) and **130 scheduled** (R26–R38). All 20 clubs' running standings reconcile with the completed league fixtures. Vasco is **ninth**, **38 points**, **25 played**, **11 wins, 5 draws, 9 losses**, **36 GF, 37 GA**.

Last Vasco match: **Vasco 3–2 Palmeiras**, fixture **322**, September 26 at 16:00, R25. Goals: Flaco López 29', Felipe Anderson 34', Facundo Colidio 38', Carlos Vinícius 78', Johan Rojas 82'. Rojas' substitution precedes his goal in database ID order, both at minute 82. xG 1.34–1.47; shots 11–13; on target 7–7; Vasco possession 56%; attendance 19,638. This result was recovered from existing records and never simulated in Phase 0.

Next Vasco fixture: **Mirassol vs Vasco**, October 3, 2027, **16:00**, R26, status `scheduled`, goals NULL. Other R26 games begin October 2; that does not change the identity of Vasco's next match.

Vasco is out of the Carioca (semifinal; Botafogo champion), Sudamericana (Group A third, six points, route `eliminated`) and Copa do Brasil (R16, Fluminense 4–3 aggregate). The universe contains **96 final Libertadores group fixtures**, **96 final Sudamericana group fixtures**, **48 played Copa do Brasil legs**, with the next 8/8/4 knockout ties unplayed despite overdue dates.

There are **547 player records**, **9 transfers**, **64 user tables** plus `sqlite_sequence`, and **331 final main-table fixtures**: 250 league 2027, 71 historical league, five Carioca and five Copa do Brasil records. Separate cup/continental tables are not part of that 331 count. The archive contains the 20-team final 2026 table; Vasco's 2026 final record is 14th, 46 points, 12W 10D 16L, 46–51. Granular 2026 coverage is partial.

Restricted football ledger cash: **R$31,930,000**, with August payroll missing. Remaining fee authorization: **R$1,400,000** from R$68m approved / R$66.6m committed. Incremental annual wages: R$22m authorized / R$21.66m committed / **R$340,000** headroom. Scouting/agents: **R$2,190,000** remaining. Emergency reserve **R$16m**, untouched and restricted. Infrastructure/debt allocations are separate categories, not transfer money.

The earlier history and narrative remain in the unmodified handoff documents and episode report. No missing historical facts were filled in, and no historical records or saves were changed.
