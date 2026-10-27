# THE BRAGA ERA

Task 03C (0.6.0) adds proposed committed continental draws through both finals,
ET/penalty eligibility, full-season stress evidence, compact restorable packages
and a separately signed forward authorization profile. **No official gameplay is
authorized.** Review the [report](docs/task03c_report.md),
[commissioner decisions](docs/task03c_decisions.md), [calibration](docs/task03c_calibration.md)
and [Hikari runbook](docs/official_play_runbook.md).

```sh
python -m braga_era world create --db output/accepted-046c/database.sqlite --output output/readiness-world --seed readiness-example-fixed-v1 --policy readiness-v2
python -m braga_era.gameplay output/readiness-world next
python tools/stress_season.py --db output/accepted-046c/database.sqlite --output output/readiness-season --seed task03c-final-a-fixed-v1
```

The last command calculates/restores a complete **noncanonical** remaining-2027
season. Its private reports contain spoilers; normal Hikari output follows the
narration cursor. Production authorization is an explicit Python API, separate
from software/policy acceptance; DEV exports remain unpromotable.

One continuous fictional football universe. **Save 046C v2 is the accepted administrative checkpoint.** Task 03B integrates the headless engine with a chronological world, proposed fictional foreign squads, player state, competition adapters and safe portable persistence. Development simulations are **NONCANONICAL DEVELOPMENT TEST** only. Original Save 046, rejected v1 and accepted v2 remain preserved. Python 3.11+; standard library at runtime.

Vasco beat Palmeiras **3–2** on September 26, 2027. Vasco is ninth with 38 points (11W, 5D, 9L; 36–37), after 25 rounds. Next: **Mirassol vs Vasco, October 3, 2027, 16:00, R26**, still scheduled. The fictional clock remains **2027-09-26 23:30**.

## Setup and use

From the repository root, with Python 3.11+ available as `python`:

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then:

```sh
python -m pip install -e ".[dev]"
python tools/bootstrap_handoff.py
python tools/bootstrap_accepted.py --download --output output/accepted-046c
python -m braga_era inspect
python -m braga_era audit
python -m pytest
```

You can run inspection, auditing and extraction directly from the repository without installing anything. Installation is needed for the `braga-era` executable and for running from other directories. Only testing requires pytest.

In this checkout a prepared environment is available without activation:

```powershell
.\.venv\Scripts\python.exe -m braga_era inspect
.\.venv\Scripts\python.exe -m braga_era audit
.\.venv\Scripts\python.exe -m pytest --basetemp .tmp/pytest
```

The extractor authenticates the original ZIP and every manifest entry, rejects unsafe paths, and refuses to overwrite altered extracted files. Repeating it with an unchanged handoff is safe. The original ZIP and nested backup chain remain untouched; the reproduced contents live in ignored `data/handoff/`.

Default database: the authenticated accepted registry, or an exact-hash installation at `output/accepted-046c`, `output/ci-accepted` or `output/Save046C_v2`. If no accepted installation exists, commands fail with installation instructions. Old Save 046 requires an explicit historical `--db`; it is never a silent default. Installing the released archive does not promote or create a registry. Override with an absolute or working-directory-relative argument:

```sh
python -m braga_era inspect --db /path/to/braga_save.sqlite
python -m braga_era audit --db /path/to/braga_save.sqlite --json
python -m braga_era inspect --db output/accepted-046c/database.sqlite
python -m braga_era audit --db output/accepted-046c/database.sqlite
```

Path precedence is `--db`, then `BRAGA_ERA_DB`, then the hash-verified accepted registry, then known exact-hash accepted installations. `BRAGA_ERA_REGISTRY` overrides the pointer location. A corrupt or missing registered checkpoint fails closed. Wheel installations outside this checkout should set `--db` or `BRAGA_ERA_DB`. Both commands support `--json`. `braga-era` accepts the same arguments.

## Chronological development world

```sh
python -m braga_era world demo --db output/accepted-046c/database.sqlite --output output/my-world-demo --seed task03b-world-demo-v1
python -m braga_era world audit output/my-world-demo/world
python -m braga_era world narrate output/my-world-demo/world --fixture league:332 --count 1
python -m braga_era save verify output/my-world-demo/NONCANONICAL_DEV_03B.zip
python -m braga_era save restore output/my-world-demo/NONCANONICAL_DEV_03B.zip --output output/my-restored-test-world
```

The complete demo generates stable proposed squads inside an additive schema, processes all 16 September 30 continentals and existing month-end payroll, captures a pregame-only Mirassol preview, then processes all ten R26 fixtures on the disposable world. It proves resumption does not reroll results and independently restores/replays the portable `DEV-03B` package. That package cannot be promoted as 047. No accepted data or official clock changes.

For controlled steps use `world create`, `world preflight`, `world advance --before-fixture league:332` or `--until "2027-10-03 23:59"`, `world preview`, `world export` and `world report`. Normal summaries contain counts rather than the future Vasco result or resulting table; explicitly private diagnostic files hold complete results, standings and state changes. Normal narration reveals only the selected match in sequence.

See [world architecture and policies](docs/world_integration.md), [Task 03B report](docs/task03b_report.md), [spoiler-safe demonstration evidence](docs/demos03b/README.md) and [Task 03C plan](docs/task03c_plan.md). Foreign-roster and knockout policies remain proposals; undrawn continental later-round reservations fail closed until a draw policy is authorized.

Audit exit codes: **0** = profile passes (warnings still listed); **1** = failed invariant, or warnings under `--strict`; **2** = input/open/query error. Audit selects the strict registered profile for the recorded save version. For 046C it requires an authenticated parent, defaulting to the package's adjacent `parent.sqlite`. Explicit `--profile 046` still rejects 046C; neither profile was weakened. Immutable package reports retain their original candidate-era wording; acceptance is recorded separately.

## First playable engine

The sandbox copies the source into a new output directory, records the input/configuration/seed commitment before draws, selects both teams autonomously, runs the pure engine and independently replays the complete result. It proves source and scratch database hashes unchanged. It never applies the result to SQLite.

```sh
python -m braga_era sandbox --db output/accepted-046c/database.sqlite --output output/my-league-demo --fixture league:333 --seed task03a-engine-smoke
python -m braga_era sandbox --db output/accepted-046c/database.sqlite --output output/my-vasco-demo --synthetic --seed task03a-vasco-synthetic
python -m braga_era narrate output/my-vasco-demo --count 1
```

Start Hikari with `preview.json`, then consume `narrate` in sequence. Postmatch statistics appear only with `FINAL_WHISTLE`. `private_match_report.json` and `private_events.jsonl` contain complete diagnostic spoilers and must not be supplied as normal pregame context. Reopening narration resumes the stored cursor without simulating again. The files are not encrypted or an access-control boundary.

The [complete demonstration reports](docs/demos/README.md) contain Palmeiras–Goiás (a real scheduled fixture, simulated only in a disposable sandbox) and a separate synthetic Vasco–Fluminense match. All 16 September 30 continental fixtures fail roster preflight because foreign player records are absent. No foreign squads were invented. Extra time, penalties, official persistence and bracket progression await Task 03B.

See [engine/configuration/seed policy](docs/engine.md), the [Task 03A report](docs/task03a_report.md), and [Task 03B plan](docs/task03b_plan.md).

## Accepted 046C and portable saves

The [durable release](https://github.com/Lbragaa/FootballSimulatorStuff/releases/tag/save-046c-v2) contains the exact accepted ZIP, separate approval receipt and SHA256 inventory. The [accepted ZIP](https://github.com/Lbragaa/FootballSimulatorStuff/releases/download/save-046c-v2/Save046C_v2_accepted.zip) hashes to `df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`; its database hashes to `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`. `tools/bootstrap_accepted.py --archive PATH --output FRESH_DIRECTORY` also works offline. Restore exact released bytes; SQLite/compression versions may make a platform rebuild byte-different. A rebuild never receives automatic acceptance.

Create a new candidate directory; existing outputs and the preserved handoff cannot be overwritten:

```sh
python -m braga_era save create --parent data/handoff/canonical/braga_save.sqlite --output output/Save046C_v2
python -m braga_era inspect --db output/Save046C_v2/database.sqlite
python -m braga_era audit --profile 046C --db output/Save046C_v2/database.sqlite --parent data/handoff/canonical/braga_save.sqlite
python -m braga_era save verify output/Save046C_v2
python -m braga_era save export output/Save046C_v2 --output output/Save046C_v2_candidate.zip
python -m braga_era save verify output/Save046C_v2_candidate.zip
python -m braga_era save restore output/Save046C_v2_candidate.zip --output output/restored-046C-v2
```

The accepted artifact remains under `output/Save046C_v2/`; its exact original ZIP is `output/Save046C_v2_candidate.zip`, also published byte-for-byte as `Save046C_v2_accepted.zip`. Original `output/Save046C/` and `output/Save046C_candidate.zip` are the **rejected v1** proposal, preserved unchanged. Verification authenticates both registered revisions; v1 is blocked from promotion. Explicit `--revision v1` is only for archival reproduction. Re-running creation needs a **new** output name and is an unaccepted reproduction. Outputs are ignored. The explicit Python acceptance API registered exact v2 under Task 03A; there is no promotion CLI.

Export and restore the original parent independently:

```sh
python -m braga_era save export data/handoff/canonical/braga_save.sqlite --output output/Save046_parent.zip
python -m braga_era save restore output/Save046_parent.zip --output output/restored-046
python -m braga_era audit --db output/restored-046/database.sqlite
```

Packages contain database(s), version/parent/schema metadata, a full-file manifest, validation reports and the permanent historical baseline. Candidate packages additionally contain deterministic operation/complete row-change logs, calendar plan/feasibility and financial statements. Restore authenticates the manifest **and** replays the authorized profile before atomically publishing a new directory. Checkpoint verification reads the database; it never trusts a stored PASS label or a rewritten manifest as permission to change history.

The calendar solver can be exercised without creating a save:

```sh
python -m braga_era calendar --db data/handoff/canonical/braga_save.sqlite
python -m braga_era calendar --strategy compare
python -m braga_era calendar --strategy C
python -m braga_era calendar --strategy B --travel-buffer-hours 6
```

The default is revised strategy B. The comparison evaluates A (cup-only, no feasible witness in this model), B (controlled league adjustment) and C (January 2028 exception). B finishes CDB on December 4, Libertadores on December 7 and Sudamericana on December 21. It changes 70 future kickoffs: 36 calendar dates and 34 times only, pinning Mirassol–Vasco on October 3 at 16:00. Return legs are three to seven days apart, no new rest shortfall is introduced, and one inherited league exception remains. December 22–January 5 is a hard blackout.

The 72h rule remains kickoff-to-kickoff including travel; it is never reduced. An extra-six-hour travel sensitivity makes this balanced family infeasible and is reported rather than silently relaxed. Foreign domestic calendars and actual routes remain unknown. Task 03A explicitly accepted the full B inventory, travel/rest scope, inherited 69h Coritiba exception, payroll convention and objectives. The accepted calendar needs no 2028 extension. C remains an unused alternative with season/contract/preseason/finance consequences.

## Protection and current limitations

Canonical/query connections use SQLite `mode=ro`, `query_only=ON` and an authorizer that denies writes, attachments and unsafe PRAGMAs. All original 64 user tables, the schema and 331 completed main-table fixtures retain their frozen fingerprints. The 046C profile permits only a specific independently replayed migration on a scratch copy. Tests that exercise corruption modify independent temporary copies only.

Original 046 warnings include 20 overdue cup ties, missing August payroll, stale objectives and inherited history quality gaps. Both candidate revisions settle August's R$1.38m payment, accrue **R$1,559,000.01** for September without a cash debit, and reconcile cup objectives. Cash is **R$30.55m**; fee authority **R$1.4m**, annual wage commitments **R$21.66m**, emergency reserve **R$16m** remain unchanged. The v2 profile also proves all 331 completed fixture rows unchanged while permitting only exact logged scheduled kickoff changes. Historical data-quality warnings remain.

See the [Task 02B report](docs/task02b_report.md), [Phase 2 engine design](docs/phase2_engine_design.md), [historical Phase 1 report](docs/phase1_report.md), [checkpoint format](docs/checkpoints.md), [payroll policy](docs/payroll_policy.md), [canonical history](docs/canonical_history.md), and [roadmap](docs/roadmap.md).

Only labeled noncanonical sandbox matches have been simulated. No official match was executed, no Save 047 created and no fictional date advanced. Mirassol–Vasco R26 remains scheduled.
