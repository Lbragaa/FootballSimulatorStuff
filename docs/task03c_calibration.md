# Task 03C calibration evidence

All trials are NONCANONICAL DEVELOPMENT TEST. No trial result enters a fixture table. Fixed seeds are enumerated before analysis; there is no outcome search.

Command: `python tools/calibrate_world.py output/task03c-calibration-world --count 1200 --output output/task03c-calibration.json`. Machine-readable evidence: [task03c_calibration.json](validation/task03c_calibration.json).

| Configuration / club-strength gap | n | Home / draw / away | Goals | Shots | xG | Reds | Injuries |
|---|---:|---|---:|---:|---:|---:|---:|
| braga-headless-1.0.0:gap-15 | 200 | 15.0% / 30.5% / 54.5% | 2.715 | 21.555 | 2.7107 | 53 | 3 |
| braga-headless-1.0.0:gap0 | 200 | 53.0% / 30.0% / 17.0% | 2.695 | 21.8 | 2.73984 | 44 | 2 |
| braga-headless-1.0.0:gap15 | 200 | 89.5% / 9.5% / 1.0% | 2.825 | 22 | 2.69462 | 63 | 4 |
| braga-headless-1.1.0:gap-15 | 200 | 19.0% / 22.5% / 58.5% | 2.56 | 21.905 | 2.70767 | 47 | 2 |
| braga-headless-1.1.0:gap0 | 200 | 61.5% / 21.0% / 17.5% | 2.88 | 21.67 | 2.75038 | 58 | 1 |
| braga-headless-1.1.0:gap15 | 200 | 89.5% / 7.5% / 3.0% | 2.815 | 22.225 | 2.6979 | 41 | 3 |

These are 200 independent seeds per cell: the maximum approximate binomial 95% half-width is 6.9 percentage points. Cells are sensitivity experiments, not estimates of an entire league. Gap zero sets club strengths equal but retains the actual Palmeiras/Goias player attributes and coach traits from league:333; it is not an identical-team experiment. Gap +/-15 changes club strength and XI OVR/attack together. The strong monotonic strength response is observable, but club and player effects cannot be identified separately by this experiment.

The accepted database records 250 completed 2027 league matches at 2.832 goals/match; 71 recorded 2026 league matches average 2.40845. Historical coverage is selected and those seasons are not independent calibration samples. Simulated cell means are 2.56-2.88 goals and about 22 shots/match. The report includes xG, rating, fitness percentiles and scoreline frequencies. No fit targets Vasco outcomes.

Forward configuration braga-headless-1.1.0 increases selection fitness weight from .05 to .12 and removes home xG advantage for proposed neutral single finals (1.375/1.375). The regulation probability model is otherwise unchanged. Engine 1.0.0 and its two regression results remain supported. New configuration identity changes RNG commitments even where numerical inputs happen to coincide; do not compare individual seeds as paired outcomes.

Rare events remain uncertain: the six cells contain 306 player dismissals in 1,200 matches and 15 injuries. Dismissals include second cautions, not only the .035 straight-red probability per team. The inherited events table records GOAL, SHOT_SAVED, SUB/SUBSTITUTION and YELLOW, with no reliable red/injury observation series. Absence of historical red records is not evidence that red cards cannot happen. The injury rate and fixed five-day absence are inherited modeling priors, not medically calibrated facts. Recommend an explicit commissioner decision on rare-event incidence/severity before official play; changing these values requires another forward configuration and new evidence.

Foreign roster review: all 49 modeled clubs retain the 1,276 V1 fictional identities and immutable provenance. Depths 24/25/26/27/28 occur for 11/7/11/9/11 clubs. Each roster has three goalkeepers and a mixed outfield reserve. Club power ranges 69.1-80; average squad OVR ranges 66.796-77.818. The JSON lists each club, positional counts, GK distribution and starter/reserve OVR gap. Recorded LIB power and documented SULA pot/group-points priors remain separate evidence types. Nationality, age, salary and historical appearances are not invented. Three GKs at every club is a deliberate availability floor, not observed history.

There is no independent evidence that justifies changing the committed V1 foreign player identities/attributes. Retain the proposed roster version for this review. Its limited strength range, generic names, missing ages and uncertain countries are disclosed limits; accepting the roster does not accept any match or seed. Fitness recovery remains 1.5 points per elapsed day, with exact appearance stints and one shared cross-competition state; the full-season artifacts provide longer-run sensitivity evidence. No autonomous transfer market or invented training workload is introduced.

Recreate the original calibration inputs on a fresh installation before running
the command above (the exact accepted parent path may differ):

```text
python -c "from braga_era.world.storage import create; from braga_era.world.policy import ReadinessPolicy20; create('output/accepted-046c/database.sqlite','output/task03c-calibration-world','task03c-calibration-fixed',ReadinessPolicy20())"
```

This pins the preserved preliminary 2.0 world input identity used for this Monte
Carlo. It evaluates regulation configurations 1.0.0 and 1.1.0; the later 2.1
shootout eligibility correction does not enter these regulation-only trials.
