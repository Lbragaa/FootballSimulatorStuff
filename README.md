# THE BRAGA ERA

One continuous fictional football universe. **Save 046 remains accepted canonical history.** Phase 1 adds an isolated **candidate 046C**, transactional administrative reconciliation and portable verified checkpoints. Python 3.11+; no runtime dependencies or external services.

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

Default database: `data/handoff/canonical/braga_save.sqlite`, located relative to the package's repository directory rather than the shell's current directory. Override with an absolute or working-directory-relative argument:

```sh
python -m braga_era inspect --db /path/to/braga_save.sqlite
python -m braga_era audit --db /path/to/braga_save.sqlite --json
```

Path precedence is `--db`, then `BRAGA_ERA_DB`, then the repository default. Wheel installations outside this checkout should set `--db` or `BRAGA_ERA_DB`. Both commands support `--json`. `braga-era` accepts the same arguments.

Audit exit codes: **0** = profile passes (warnings still listed); **1** = failed invariant, or warnings under `--strict`; **2** = input/open/query error. The default audit still validates the exact **046** baseline. It deliberately rejects 046C unless the explicit profile and authenticated parent are supplied.

## Candidate 046C and portable saves

Create a new candidate directory; existing outputs and the preserved handoff cannot be overwritten:

```sh
python -m braga_era save create --parent data/handoff/canonical/braga_save.sqlite --output output/Save046C
python -m braga_era inspect --db output/Save046C/database.sqlite
python -m braga_era audit --profile 046C --db output/Save046C/database.sqlite --parent data/handoff/canonical/braga_save.sqlite
python -m braga_era save verify output/Save046C
python -m braga_era save export output/Save046C --output output/Save046C_candidate.zip
python -m braga_era save verify output/Save046C_candidate.zip
python -m braga_era save restore output/Save046C_candidate.zip --output output/restored-046C
```

The reviewed candidate from this task is under `output/Save046C/`; its ZIP is `output/Save046C_candidate.zip`. Re-running creation needs a **new** output name. These are ignored local artifacts, not committed binaries. Acceptance is separate; **there is no promotion CLI** and the original default database remains 046.

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
python -m braga_era calendar --travel-buffer-hours 6
```

The second command reports no solution under the stricter model. The candidate proposal uses **72h kickoff-to-kickoff including travel**, reserves undrawn later rounds for every possible qualifier and preserves all league dates. It discloses 12 inherited league rest shortfalls, unknown foreign domestic schedules, long inter-leg gaps, December 25 semifinals and December 28/31 finals. **These calendar choices and the proposed actual-day/month-end payroll policy need commissioner acceptance.** The schedule is conditionally feasible, not an unqualified global-calendar guarantee.

## Protection and current limitations

Canonical/query connections use SQLite `mode=ro`, `query_only=ON` and an authorizer that denies writes, attachments and unsafe PRAGMAs. All original 64 user tables, the schema and 331 completed main-table fixtures retain their frozen fingerprints. The 046C profile permits only a specific independently replayed migration on a scratch copy. Tests that exercise corruption modify independent temporary copies only.

Original 046 warnings include 20 overdue cup ties, missing August payroll, stale objectives and inherited history quality gaps. The unaccepted 046C candidate reschedules those ties, records August's R$1.38m payment, accrues **R$1,559,000.01** for September without a cash debit, and reconciles cup objectives. Candidate restricted cash is **R$30.55m**; fee authority remains **R$1.4m**, annual wage commitments **R$21.66m**, emergency reserve **R$16m**. Historical data-quality warnings remain. See [known issues](docs/known_issues.md).

See the [Phase 1 report](docs/phase1_report.md), [checkpoint format and storage](docs/checkpoints.md), [payroll policy](docs/payroll_policy.md), [Phase 0 report](docs/phase0_report.md), [canonical history and checksums](docs/canonical_history.md), [architecture](docs/architecture.md), [schema guide](docs/schema.md), and [roadmap](docs/roadmap.md).

No matches have been simulated and no fictional dates advanced. Candidate 046C has not been promoted.
