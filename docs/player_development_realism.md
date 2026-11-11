# Player development and match realism candidate

Worker candidate 0.13.10 pairs `braga-headless-1.3.0` with `ability-development-2`. Production inspection at the start of this work found worker 0.13.9, match engine 1.2.0, and accepted checkpoint `a1758f12d001fe0a1a7fb36d81a85cf511202cb8d5d38c477785fbedcfa4edc2` on `the-braga-era-libertadores-2028`. Its accepted simulation clock was June 28, 2028 at 17:33. The bridge’s narration backlog is independent of that clock. All candidate execution took place in development.

## Audit

| System | Current path and finding |
| --- | --- |
| Permanent abilities and age | `multiseason/market.py` and `multiseason/offseason.py` already persist annual before/after records in `ms_attributes` and update `world_players.attributes_json`. Both apply essentially the same scalar to OVR and every skill. Registered offseason tracks modeled age, retirement and youth intake. Native career-phase and potential data vary in coverage. |
| Temporary performance | `world/players.py` and `multiseason/execution.py` load match-day players, project elapsed fitness recovery, and apply postmatch form, morale, fitness, injuries and sanctions. Underlying skill is separate. Permanent changes are read from the current player record when building the next unclaimed fixture. |
| Training | The existing dated world training entries are short-term team quality effects with consumption records. Their availability varies by world profile. There are no individual practice observations or measured coaching improvements suitable for fitting a long-term training model. |
| Team quality and opportunities | `engine/coaches.py` selects starters using role suitability, OVR, fitness, form and bounded manager noise. Formations select roles and tactics influence shot rates. `engine/match.py` blends the club strength prior with effective XI quality, then applies separate finishing, composure and keeper effects. Raising club strength and all player skills together was particularly influential in calibration. |
| Goals and statistical output | The engine samples shots by team and time, assigns active shooters, and derives on-target and goal outcomes using chance quality and actor attributes. xG sums event-level expected goals. Possession and player ratings are model outputs, and the calibration below does not establish real-world accuracy for them. |
| Discipline and time | Regulation scheduled a bounded Poisson caution count and separate straight-red draws. Position alone weighted caution recipients, leaving booked defenders fully exposed to further cautions. Extra time used a different uniform recipient policy and omitted the same live numerical effect used in regulation. Active-player removal, stints, goalkeeper emergencies, second-yellow sequencing, and competition-specific sanction enforcement already existed. |
| Coaching, injuries and knockouts | Engine 1.2 has stint-aware substitutions and booked-player protection in its outgoing heuristic. The candidate retains those choices, substitution windows and quotas, penalty-taker eligibility, aggregate resolution and shootout scoring. Current injuries remain coarse, generally a five-day absence in the existing world rules. |
| Checkpoint and timeline | Registered succession signs the exact manifest and keeps fixture config, input and seed commitments. Old profiles continue to replay using their recorded versions. Profile activation is a separate operation on the currently authenticated accepted head. Reveal cursors live in the authority separately. |

## Permanent development

The annual preseason boundary uses the existing offseason transaction and player/season primary key. Per-match updates would increase write and replay overhead and magnify noisy match ratings. Calendar-month updates would need a new obligation schedule. The annual model reads the immediately prior year's final fixture participation, restricted to the post-activation window, and prorates the first annual adjustment. Old matches remain part of history with no retroactive development credit. Exact retry returns the previously committed operation, while a duplicate player-season application fails the existing uniqueness/consumption guard.

Position determines which skills can change and their weight in OVR. For instance, attack carries 48% of a forward's rating and goalkeeping carries 64% of a keeper's. A signed-record offset reconciles each inherited OVR with its starting attributes. The model changes those attributes, then calculates OVR from their changes. A tested prospect moved into the autonomous XI and raised its expected goals. Attack, composure and goalkeeping also have direct effects when resolving chances. Defense and passing primarily influence this implementation through role-weighted OVR, alongside existing effective-XI calculations.

Default peak ages are 25 for forwards, 26 for midfielders, 27 for defenders and 29 for goalkeepers, with a stable per-player variation of up to two years. The age evidence supports position-dependent outfield curves and faster physical decline. The goalkeeper curve and exact coefficients are modeling assumptions. The first skill profile uses registered modeled lifecycle age where available. Otherwise a stable, labeled age prior uses any documented career phase as a weak clue. A phase hint is no substitute for a known birthdate. No bios are imported. [Outfield peak-age study](https://journals.sagepub.com/doi/10.3233/JSA-160021) · [Age and match performance study](https://www.sciencedirect.com/science/article/pii/S1440244022000469)

A stable learning pace, role-adjusted peak, and uncertain headroom differentiate players. Native potential, where usable, is only a bounded input to headroom. 58% of the growth opportunity is modeled as ordinary practice and 42% can come from recorded minutes, capped at 2,100 minutes per season. Match goals, ratings and starter status do not award extra growth. Injury observations can reduce learning by up to 30%, and injury events do not directly subtract permanent skills. The model includes random variation, smaller late-prime gains, physical-led decline and yearly per-skill bounds of −2.7/+2.0. Temporary modifiers, contracts and health records use their established paths. The existing retirement and youth operations still apply.

Both offseason entry points write their exact forward evidence and trajectory to existing `ms_attributes.assumption_json`. This is a versioned logical migration with unchanged table layout. It avoids a rewrite of inherited ratings or a separate mutable development database. Transfers use the same stable player IDs. Different worlds use their own signed seeds and operate on separate authority and world state. The existing career-statistics development report reads before/after ability changes without exposing the latent profile.

## Disciplinary and match balance

The documented 1,200-match study in [Task 03D decisions](task03d_decisions.md) recorded 306 dismissals, of which 225 were second yellows. The current 1.2 comparison reproduced the mechanism under a different synthetic fixture set. The high second-yellow share was a consequence of recipient selection as well as card volume. Altering straight reds alone would leave that interaction intact.

| Setting | 1.2.0 | Candidate 1.3.0 |
| --- | ---: | ---: |
| Poisson regulation cautions, per team | 1.55 | 2.55 |
| Maximum generated regulation cautions, per team | 4 | 8 |
| Regulation straight red probability, per team | .035 | .035 |
| GK / DF / MF / FW caution exposure | .2 / 2 / 1.5 / .6 | .30 / 1.35 / 1.20 / .80 |
| Already-booked recipient caution multiplier | 1.00 | .16 |
| Club prior / effective XI weights | .71 / .29 | .64 / .36 |
| Expected-goals strength slope | .054 | .042 |

Recipient selection now includes a bounded composure multiplier (.85–1.15) and uses the same candidate policy in both periods. The repeat-caution weight leaves legitimate second yellows possible. Card occurrence is still independent of fouls and match state. Extra time uses the same 10% per missing player own xG penalty and 7.5% opponent opportunity boost as regulation, with the existing floor. The candidate also slightly reduces goalkeeper, composure and finishing coefficients to limit overlapping effects of correlated ratings. Starting home advantage, injury rates, added time, goal resolution and legacy substitute rules were retained.

The current competition counters add the match's recorded cautions to the accumulation tally and also impose a dismissal ban. A second yellow can therefore contribute to an additional threshold ban. This candidate retains the established competition policy. Increased cautions may raise accumulation bans even as dismissals fall. Formal adjudication for a regulation match reduced below seven players remains unmodeled. The extra-time validator already rejects a short-handed abandonment.

The CBF's 2024 Série A table sums to 2,070 cautions (5.45 per match), 163 red-card entries (0.43 per match) and 929 goals (2.44 per match) in 380 matches. Its aggregate table does not identify second yellows, player-position exposure, or matches with a dismissal. EURO 2024 recorded 166 cautions and three red cards in 36 group games. The 2022 World Cup recorded 227 cautions and four dismissals in 64 games, with one straight red and three second yellows. These samples use different competition conditions and the latter two have small red-card counts. The candidate's 0.153 dismissals per simulated fixture falls between the international and CBF aggregate frequencies, but does not establish Série A-specific fit. [CBF 2024 Série A](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/2024?csrt=12294439037593773336) · [UEFA group-stage report](https://www.uefa.com/uefaeuro/history/news/028e-1b3d98f65cc9-b1855a1aaae1-1000--positive-start-for-euro-2024-referees/) · [FIFA 2022 tournament statistics](https://vod.fifa.com/tournament-organisation/world-cup-2022-in-numbers/fifa-world-cup-qatar-2022-at-a-glance)

## Disconnected calibration

Run `python -m tools.calibrate_realism_candidate` from the source checkout. The script validates each regulation match and cup resolution and uses 300 predetermined seed labels per scenario per version. Versioned inputs yield their own commitments. The comparison evaluates distributions rather than expecting equal results between configurations. The cup cell uses neutral venue, unequal congestion and shallower benches, and includes extra time.

| Metric | 1.2.0 | 1.3.0 |
| --- | ---: | ---: |
| Fixtures with a dismissal | 241/1,200 (20.08%) | 170/1,200 (14.17%) |
| Straight / second-yellow dismissals | 84 / 187 | 85 / 98 |
| Defender dismissals per 1,000 player-minutes | 0.176 | 0.094 |
| Cautions per fixture | 3.15 | 5.28 |
| Goals per fixture | 2.90 | 2.91 |
| Shots / on target per fixture | 22.45 / 9.39 | 22.59 / 9.43 |
| xG per fixture | 2.80 | 2.78 |
| Five or more goals | 172 / 1,200 | 177 / 1,200 |
| Injuries / substitutions | 17 / 7,058 | 26 / 7,065 |
| Mean player rating | 6.61 | 6.61 |
| Equal-strength home / draw / away | 49.7% / 25.3% / 25.0% | 46.0% / 26.3% / 27.7% |
| Strong club wins, home / away cells | 89.7% / 83.7% | 86.0% / 75.7% |
| Cup extra-time / shootout resolutions | 86 / 42 | 89 / 41 |
| Median engine-only time range by cell | 4.48–4.99 ms | 4.43–4.78 ms |
| p95 engine-only time range by cell | 5.18–6.76 ms | 4.70–7.27 ms |

Wilson 95% intervals for at least one dismissal are approximately 17.9–22.4% and 12.3–16.3%. The equal-strength cell had 55 dismissal matches in both versions. The aggregate result depends on the scenario mix and does not imply every pairing gets fewer reds. A 17-point club gap combined with uniformly stronger players remains a strong advantage. These elapsed times exclude database work, signing, packaging, replay and bridge latency.

The same tool runs five independent cohorts of 240 players over ten seasons. They begin at OVR 70. The table compares means. Veterans who would ordinarily retire were intentionally retained for the aging stress test.

| Starting profile | Candidate year 1 | Candidate year 5 | Candidate year 10 | Legacy year 10 | No gain in candidate year 1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Defender, 18 | 70.58 | 72.14 | 72.75 | 74.13 | 9 |
| Forward, 18 | 70.52 | 71.81 | 72.19 | 74.13 | 11 |
| Midfielder, 25 | 70.15 | 70.24 | 67.50 | 67.93 | 48 |
| Defender, 32 | 69.61 | 65.74 | 56.97 | 63.13 | 199 |
| Goalkeeper, 32 | 69.93 | 68.16 | 61.76 | 63.13 | 148 |

In these illustrative simulations, one teenage defender reached 73.50 at year five and 73.83 at year ten. One teenage forward was at 71.71 after five years and 71.43 at year ten. One 32-year-old goalkeeper reached 69.73 at year five. The synthetic cohorts test dispersion and caps. Long-run economy, youth intake and club-strength equilibrium require a whole-world rehearsal.

## Production boundary

The candidate independently restored the exact production qualifying archive with full-history audit using a disposable registry snapshot made through a read-only SQLite connection. The mixed-engine integration test signs a 1.1 → 1.2 → 1.3 development sequence, preserves every inherited result digest, checks the new commitment configuration, independently exports and restores the mixed history, and verifies the original parent hash.

A separate registered-authority rehearsal used the archived `season-boundary-test` authority and its public TEST key. It refused delegated and combined activation, accepted the signed 1.2 and 1.3 zero-match successors, resumed the 1.3 operation after an interruption, and returned the same exact checkpoint on repeated acceptance. The independently restored 1.3 successor `6c8a580e6d50b2ada9d3b91fcd0c17625b9288755939c800ed2b98c924da2497` retained all 1,368 original fixture result digests and the same clock. The entire rehearsal, including both activations and portable restores, took 556.3 seconds on Windows.

The isolated installation check used wheel SHA-256 `9bb6c93084d566c871559e88653cebc6909fea96ba7f795683cf4dd4a2412259`. Once the commissioner approves the balance, verify the then-current head and command ledger, drain any executing request and independently check the backup. Use a fresh request UUID and the exact authenticated head to prepare the operation below. [Release runbook](production_release_candidate.md) · [Signed activation procedure](substitution_policy.md#future-production-activation)

```python
operations = [{
    "kind": "activate_realism",
    "args": {
        "engine_version": "braga-headless-1.3.0",
        "development_policy": "ability-development-2",
    },
}]
manifest = season_lineage.prepare(registry, key, request_id, operations)
```

The API refuses an unregistered parent, another active version, an unfinished fixture claim, a combined batch, or delegated ordinary gameplay. Separately sign execution and exact candidate acceptance and independently restore the result. Verify that it produced zero matches, check the policy selected for the first unclaimed commitment, and verify the worker's unchanged narration cursor and bridge sequence before resuming ordinary gameplay.

The same runtime can replay older fixtures after activation. If installation fails before activation, restore the prior runtime with the original head. After activation, use a runtime that supports 1.3.0 for recovery, because falling back to an older package would leave the new head unreadable. The accepted activation receipt remains immutable. Outcome-changing revisions need a subsequent version and independent acceptance.

The calibration supports a forward candidate. Real league calibration by competition, an explicit foul model, injury duration and recurrence, repeated all-club longitudinal rehearsals, and a live episode performance measurement are still open. The Windows installation and signed activation tests ran in isolation. The production worker was left running its existing release.
