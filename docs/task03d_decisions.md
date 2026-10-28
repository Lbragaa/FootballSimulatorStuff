# Task 03D — proposed policy bundle for commissioner review

**PENDING HUMAN REVIEW. This document grants no production approval or fixture
authority.** The canonical review inventory remains [Task 03C decisions](task03c_decisions.md).
Task 03D resolves continuity and adds controlled evidence; it does not silently
accept those proposals.

| Component | Proposed bundle | Still requires commissioner acceptance |
|---|---|---|
| Foreign rosters | Retain `fictional-squads-1.0.0`: 1,276 modeled fictional identities across 49 clubs; recorded LIB strengths and documented SULA priors; no historical backfill. | Quality/depth priors, persistent fictional identities, unknown countries/ages and absent foreign domestic workloads. |
| Historical unknowns | Preserve all recorded players, results and contracts; exclude archived #196 separately from active #354; start only forward disciplinary counters where history is unknown. | Forward eligibility/registration assumptions are not proof that historical bans or injuries never existed. |
| Regulation | Retain `braga-headless-1.1.0`, including .12 fitness selection weight. No outcome-changing configuration was justified or introduced by this task. | Football plausibility of the parameter set, club/XI weighting and rare-event incidence. |
| Discipline/injury | Retain existing cautions, second cautions, .035 straight-red probability/team and .015 injury probability/match; modeled minor injuries have five-day absence. Three cautions and dismissal penalties remain competition-specific forward bans. | High repeat-caution dismissal incidence, accumulation/reset policy and limited injury-severity model. |
| Recovery/form | Retain one shared elapsed-time state, 1.5 recovery points/day, chronological ratings/form and explicit training consumption IDs. | Fitness is a bounded availability score, not a measured medical/conditioning model; training and foreign workload gaps remain assumptions. |
| Knockout resolution | No away goals; direct penalties after tied two-leg aggregate; single finals use 30-minute ET and penalties. | Competition-specific tiebreaks where source rules are incomplete. |
| ET/shootout | Retain `braga-knockout-2.1.0`, six total substitutes, extra window, interval subs, cards/injuries, GK replacement/emergency keeper, eligible equal taker pools. Fail closed for unresolved/abandoned outcomes. | Substitution/disciplinary allowances, no ET added-time or adjudication policy. |
| Draws/brackets | Retain committed stage draws after actual qualifiers, SULA seeded R16 group winners, later open draws, CDB recorded `next_tie` route. | No invented country/group avoidance rules; administrative home ordering and approved reservations. |
| Neutral finals | Retain neutral xG 1.375/1.375; listed home/away remains administrative. | Venue/advantage assumptions; no unrecorded venue is asserted. |
| Managers | Preserve autonomous selections and match-score reactions; .12 weight demonstrably changes fatigue selection. | Aggregate-aware managerial strategy is **not added**. Accept this simplification or require a new forward version before affected return-leg authorization. |
| Finance | Existing contract-backed, idempotent actual-day payroll only; preserve authority/reserve and all settled ledger records. | No new income, awards, transfers, owner capital or financial expansion is authorized. |
| Continuity | `continuous-forward-lineage-2`, immediate accepted-parent packages, immutable career seed policy `career-stable-per-fixture-1`, separate execution/acceptance signatures for every generation. | Exact first production policy bundle/career seed commitment; provisioning and batch authority are future decisions. |
| Runtime/key | One active authority, signed state/cursor receipts, explicit transfer fencing, separate encrypted key backup. | Trusted human controls the production key and recovery/migration. A copied offline registry is not a second canonical authority. |

## Dismissals: interaction identified and bounded

The exact original 1,200 trials reproduce **306 player dismissals**: **81 straight
reds** and **225 second-yellow dismissals**. **272 matches** contain at least one
dismissal: 0.255 events/match versus 22.67% probability of any dismissal. Those are
different quantities. The straight-red count is close to the documented 0.07
scheduled events/match expectation (two teams × .035); most dismissals arise from
repeat cautions.

The engine chooses cautioned actors from the current XI with positional weights
GK .2, DF 2, MF 1.5, FW .6. It can target a previously cautioned player again.
Combined with approximately three cautions/match, this creates the observed
second-yellow frequency. It is an explicit model interaction, not duplicate
receipt application or an injury/card being imported as a historical fact.
The JSON evidence includes player, club, position, score-state and strength-cell
counts. Leading/trailing counts are descriptive, not exposure-normalized causal
rates; discipline scheduling does not directly use team strength or score.

Preregistered 300-trial identical-team alternatives:

| Analysis-only setting | Straight reds | Second yellows | Matches with a dismissal | Cautions |
|---|---:|---:|---:|---:|
| Current 1.1.0 | 20 | 76 | 86 | 953 |
| Straight-red probability .015 | 8 | 61 | 66 | 952 |
| Yellow lambda 1.2 | 29 | 33 | 58 | 700 |
| Maximum two yellow events/team | 20 | 21 | 40 | 739 |

These alternatives are **unregistered analysis configurations**, never used by a
lineage execution. Lowering straight reds alone does not remove the repeat-caution
interaction. The other options also reduce overall cautions, so there is no
evidence-backed isolated replacement that preserves every existing assumption.
Historical event coverage does not supply a reliable red/injury rate series.
Recommend retaining 1.1.0 for review, explicitly acknowledging the high combined
dismissal prior; a different commissioner choice requires versioning and reruns
before official play. No setting is selected for a Vasco result.

## Strength/home controls

Anonymous synthetic teams have identical positional distributions, attributes,
fitness, morale and coach traits. Symmetric tactics are fixed for the controlled
experiment; production coaches remain autonomous. With 300 independent seeds per
cell, identical teams produced H/D/A **43.0/30.0/27.0%**; reversing the team
identities produced **46.3/27.0/26.7%**. This isolates a home advantage without
the old Palmeiras/Goias attribute mismatch. Maximum binomial 95% half-width is
about 5.7 percentage points; identity-reversal differences fit that uncertainty.

A 15-point club-strength-only gap gave **72.3%** home wins, player-quality-only
15 gave **60.7%**, and both together gave **84.3%**. Small three-point gaps and
opposed tactical controls are in the machine-readable evidence. Strong club and
player quality compound through the documented quality and finishing mechanisms;
there is no hidden Vasco modifier. Extreme dominance remains a commissioner
plausibility choice, not an independently identified empirical coefficient.
The controlled evidence supports bounding the earlier 89.5% finding rather than
retuning the engine against the desired career.

## Recovery/selection controls

In an isolated positional contest, an OVR-80 forward at fitness 55 starts ahead
of three OVR-78 alternatives at fitness 90 under the old .05 selection weight.
Under .12 he is benched. An explicit suspension excludes him under both weights.
The existing change therefore affects actual XI choices rather than being an
unused parameter.

The evidence also runs 24 fixtures at three-day intervals with rolling form and
one elapsed recovery timeline, disabling cards/injuries only to isolate workload.
Deep equal-quality squads rotate and approach the fitness ceiling. This is a
known consequence of replenishment exceeding average per-player workload in a
26-player squad, not double recovery by different competition adapters. Do not
describe fitness 100 as medical perfection. Unknown training/travel workloads and
the energy-score ceiling require explicit acceptance; no new recovery model is
silently introduced. Actual three-batch state equality and controlled injury/ban
copy/recovery tests separately verify persistence correctness.

## Decision sequence

1. Human reviews/accepts or revises this exact bundle and its uncertainties.
2. A new explicit instruction permits production authority/key provisioning.
3. Human authorizes the exact September 30 manifest, including payroll and the
   precommitted career seed policy. Policy/software approval alone is insufficient.
4. Trusted runtime executes once, validates/restores and presents exact hashes.
5. Human separately accepts the exact successor. The next batch uses that accepted
   parent and the inherited seed; no new save-specific RNG root is allocated.

Neither this document nor successful engineering rehearsals completes any of
those production decisions. Original 046C and official fictional time remain
unchanged throughout Task 03D.
