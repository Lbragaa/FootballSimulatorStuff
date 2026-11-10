# Forward substitution policy

Worker candidate 0.13.5 supports `braga-headless-1.2.0`. Installation alone
leaves the next fixture on the career's currently accepted configuration.

## Root cause and behavior

The installed 0.13.4 engine used regulation 1.1.0 in the accepted Vasco fixtures
on January 27, February 4 and February 11, 2028. Every reported substitution
was recorded as a tactical refresh. In `engine/match.py`, a coach opportunity
walked a fixed score-dependent position order, searched the entire active group
and chose the lowest pregame fitness/form/card/goal score. The entry timestamp
and starter flag already existed for appearance accounting but were unused in
the decision. A lower-fitness bench player could immediately become the same
position's lowest-ranked active player. The old extra-time selector in
`world/knockout_v2.py` also considered all active outfielders and tried a change
at each interval.

The new selector considers eligible, unused reserves against healthy active
outfield starters. It projects freshness using actual seconds played, weights
recorded ability and the occupied tactical role, accounts for goals, assists
and booking risk, and adjusts position preference for the score. A repeat
refresh of the same line needs a greater gain, including in extra time. A
minimum gain allows no change. Bounded coach noise ranks only worthwhile
options. The normal kickoff XI and the coach's scheduled opportunities use
the existing selection framework. A deep bench retains an eligible reserve
keeper when one is available.

Injured players can be replaced regardless of how recently they entered.
After a keeper dismissal or an injury that leaves no keeper, the engine uses
a legal reserve when possible and otherwise records an outfield keeper.
A keeper replacing an outfielder after a dismissal preserves the short-handed
team count. All paths retain the existing edition rules for when extra time
is played. The default limits remain five replacements and three live
stoppages, with one more replacement and live stoppage in extra time.
Extra-time intervals consume no live stoppage. Independent audits reconcile
chronology, eligibility, stints, quotas and result data.

Tactical replacements remain same-position, with the starter's role used to
evaluate suitability. The model does not infer individual fatigue sensors,
fine-grained positional versatility, formation reshuffles or exceptional
tactical removal of a substitute. Injury and goalkeeper emergencies are the
exceptions to starter-only selection.

## Development verification

With fixed synthetic XIs and coach windows at 62, 76 and 84 minutes, requested
seed `chain-3` produced the following home decisions.

| Minute | 1.1.0 | 1.2.0 |
| --- | --- | --- |
| 62 | 9 → 13, forward | 9 → 13, forward |
| 76 | 13 → 14, forward | 8 → 16, midfield |
| 84 | 14 → 15, forward | 4 → 17, defense |

The 300 paired development fixtures varied team strength, fitness, form, OVR
and bench availability. Each configuration played 60 of those fixtures through
extra time by supplying a synthetic first-leg aggregate. The legacy run made
1,853 substitutions, including 402 tactical removals of prior substitutes.
The new run made 1,205 substitutions and zero tactical chains. Neither sample
had an emergency chain by chance. Forced scenarios cover medical chains and
keeper replacements, including a same-clock injury and a short-handed team.
The paired inputs and requested seeds are fixed. The RNG root includes the
configuration digest, so the new version has its own stream.

For 40 synthetic fixtures alternating home and neutral configurations, complete
1.1.0 match bundles including extra time and applicable penalties had the same
canonical digest under the installed worker and the development implementation.
`48e710674c8865dcf314ea72aa329d818c75de83b5c6698b1d286a313e22279d`.

A registered TEST rehearsal authenticated an archived parent and independently
replayed the signed activation successor. A repeated acceptance returned the
same checkpoint. The activation preserved the clock and all 1,368 prior
execution hashes, and played zero matches. A separate mixed-version test
claimed matches on both sides of the activation and replayed the journal with
each fixture's committed configuration.

## Future production activation

1. After explicit approval, finish and reveal the current committed episode.
   Verify the accepted registered head, signed ledger, empty bridge queue and
   absence of pending claims. Take a verified private backup. Stop the worker
   and install a verified build of 0.13.5 under the existing procedure in
   [the release runbook](production_release_candidate.md). Keep the original
   authority, seed, configuration and checkpoints.
2. At the idle registered head, use the local `braga_era.season_lineage` API
   with the existing registry and signing authority. Create a fresh UUID once
   and prepare an activation-only successor. Persist the exact manifest in the
   approved private operator location before requesting authorization.

   ```python
   operations = [{
       "kind": "activate_substitution_policy",
       "args": {"engine_version": "braga-headless-1.2.0"},
   }]
   manifest = season_lineage.prepare(
       registry, key, request_id, operations, transition=False, delegated=False
   )
   execution_statement = season_lineage.authorization(manifest)
   ```

3. After the commissioner reviews the exact immediate parent and manifest,
   obtain the signed `execution_statement`. Pass that signed envelope to
   `season_lineage.authorize(registry, key, manifest, execution_approval)`.
   Then call `season_lineage.execute(registry, key, request_id, directory)`
   at a fresh approved private destination. On interruption, reuse that UUID,
   manifest and destination. This operation records the engine activation and
   performs independent replay. It schedules and plays zero fixtures.
4. Review the verified successor. Obtain a separate signature over
   `season_lineage.acceptance_template(registry, key, directory)` and pass
   its document and signature to
   `season_lineage.accept(registry, key, directory, decision, signature)`.
   Confirm that its parent, season clock and old results match the reviewed
   checkpoint, then resume the worker and let normal play claim the next
   fixture. Its committed configuration records 1.2.0. No bridge command or
   standing grant authorizes the activation itself.
5. Old execution records retain their stored engine and configuration. Full
   replay follows the activation journal at the original point. Keep 1.2.0
   support in any later worker build once the activation successor is accepted.
   Before acceptance, software rollback uses the prior verified wheel and the
   current authority. After acceptance, never roll the career back to remove
   this policy or to change a match result.
