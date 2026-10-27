# Task 03C commissioner decision sheet

Status: **all choices below are proposals; no official execution is authorized**.
Accepted world: exact Save 046C v2, 2027-09-26 23:30. Software approval,
policy approval, execution authorization and successor acceptance are separate.

| Decision | Proposed choice and evidence | Alternative / consequence |
|---|---|---|
| Foreign squads | Retain `fictional-squads-1.0.0`: 49 clubs, 1,276 explicitly fictional players; deterministic identities, recorded LIB power and disclosed SULA priors. See calibration JSON. | Request a new roster version and rerun review. Never overwrite a previously accepted player to improve results. |
| Historical unknowns | Current membership except archived identities; honor known contracts/registration; forward bans start at zero because historical bans are unknown. | Supply authenticated additional evidence before execution. Missing observations are not assertions that no historical ban existed. |
| Regulation | Proposed `braga-headless-1.1.0`: fitness selection weight .12, unchanged regulation probability model, neutral-final xG 1.375/1.375. Keep 1.0.0 available. | Require additional calibration and a new forward configuration; never reroll a committed match. |
| Rare events | Retain documented yellow, red, injury and fixed five-day absence assumptions for the first review. Monte Carlo: 306 player dismissals and 15 injuries in 1,200 matches. | Revise rates/severity before official play. Historical data cannot independently identify these rates. No claim of empirical medical realism is made. |
| Recovery/form | One elapsed-time overlay, 1.5 fitness points/day; minutes-weighted chronological form, bounded morale, forward-only discipline per competition. | Define a new recovery/training model and rerun full season. No generic per-round recovery bonus. |
| Discipline | Three accumulated cautions trigger a one-match competition ban; dismissal adds one; serve in that club's next match in the same competition. No automatic round reset or appeal. | Supply competition-specific thresholds/resets. They cannot be inferred from missing source rules. |
| Two-leg ties | No away goals; direct penalties after tied aggregate in CDB, LIB and SULA. Preserve every settled tie. | Adopt an explicit per-competition ET/away-goal alternative with new rules version and evidence. |
| Single finals | Existing calendar's single final; neutral advantage; 30 minutes ET, then penalties. Listed home/away is administrative orientation, not a newly asserted venue. | Supply an approved venue/advantage policy. No match venue is invented. |
| Extra time | `braga-knockout-2.1.0`: ET1/ET2, interval, up to six total substitutions, one additional live window, interval substitutions, cards/injuries, emergency GK, equal shootout pools retaining the defending GK. | Different substitution allowances require a new policy. Below seven players or an unresolved 64-round shootout fails closed; no abandonment winner is invented. ET has no extra added-time model. |
| LIB future stages | After all current-stage winners exist, commit the sorted qualifier pool and deterministic named seed, then open shuffle/pair. Listed first club hosts L1, return reversed. Draw anew each stage. | Supply a fixed bracket mapping before execution. No country/group avoidance restriction is inferred. |
| SULA R16 | Eight recorded group winners versus eight actual playoff winners; seeded group winners host return leg. Pair shuffled pools after PO completion. | Approve specific group/country avoidance constraints and a new draw procedure. |
| Later SULA | Open committed stage draws, reversed second legs, single neutral final. | Approve a fixed mapping instead. No qualifiers exist before committed results. |
| CDB bracket | Keep recorded `next_tie` path. Known next-tie inputs determine participants; sorted feeder order supplies disclosed administrative first-home order. | Supply an authenticated home-order decision. Do not redraw settled pairings. |
| Calendar | Retain approved reservations and protected Mirassol kickoff. Disclose inherited Coritiba league:382 → league:393 69-hour exception. | Calendar revision needs separate authority. Foreign domestic commitments and actual travel routes remain unknown. |
| Coach realism | Autonomous selection/tactics/substitutions, no guaranteed starter or Vasco advantage. Live reactions use match score; aggregate-specific coach strategy is not modeled. | Require an aggregate-aware tactical extension and fresh forward-version evidence before authorization. |
| Finance | Existing contract-based payroll only, month-end idempotency; no invented revenue, owner capital, transfers or awards; reserve/authority unchanged. | New financial operations need explicit separate authority. |
| Trust/runtime | Provision a commissioner-controlled key and the separate `official-forward-profile-1` registry only in a subsequent authorized task. HMAC decisions bind exact manifests/candidate hashes. | Do not use an agent-held shared key as independent commissioner approval. No production key/registry is provisioned by Task 03C. |

Recommended disposition: review the numerical evidence and explicitly accept or
revise each modeling choice, particularly rare events, foreign quality, tactical
scope and disciplinary rules. A successful season/replay proves engineering
consistency under these assumptions; it does not settle football policy.

The initial forward profile pins exact 046C and the entire authorized chronological
batch, including future fixture slots and payroll. It is an initial successor
profile, not an automatic 2028 rollover or a generic migration from any arbitrary
accepted future database. A later accepted parent requires its own explicit
lineage/profile registration. No automatic promotion or dashboard is provided.

If a commissioner requires any alternative above, readiness is blocked until that
version is implemented and verified. Merely accepting this document, the roster,
or the software does not authorize September 30, Mirassol–Vasco, or Save 047.
