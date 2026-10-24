# THE BRAGA ERA

One continuous fictional football universe. **Save 046 remains accepted canonical history.** Task 02B provides revised **candidate 046C v2**, transactional reconciliation and portable verified checkpoints. The earlier v1 calendar was rejected and remains an immutable archival proposal. Python 3.11+; no runtime dependencies or external services.

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
python -m braga_era save create --parent data/handoff/canonical/braga_save.sqlite --output output/Save046C_v2
python -m braga_era inspect --db output/Save046C_v2/database.sqlite
python -m braga_era audit --profile 046C --db output/Save046C_v2/database.sqlite --parent data/handoff/canonical/braga_save.sqlite
python -m braga_era save verify output/Save046C_v2
python -m braga_era save export output/Save046C_v2 --output output/Save046C_v2_candidate.zip
python -m braga_era save verify output/Save046C_v2_candidate.zip
python -m braga_era save restore output/Save046C_v2_candidate.zip --output output/restored-046C-v2
```

The revised candidate is under `output/Save046C_v2/`; its ZIP is `output/Save046C_v2_candidate.zip`. Original `output/Save046C/` and `output/Save046C_candidate.zip` are the **rejected v1** proposal, preserved unchanged. Verification authenticates both registered revisions; v1 is blocked from promotion. Explicit `--revision v1` is only for archival reproduction. Re-running creation needs a **new** output name. Outputs are ignored, not committed binaries. There is no promotion CLI and the default database remains 046.

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

The 72h rule remains kickoff-to-kickoff including travel; it is never reduced. An extra-six-hour travel sensitivity makes this balanced family infeasible and is reported rather than silently relaxed. Foreign domestic calendars and actual routes remain unknown. The candidate requires commissioner acceptance of the full date inventory, travel/rest scope and inherited exception; supported payroll directions do not authorize automatic promotion. The recommendation needs no 2028 extension. The optional C alternative does and carries season/contract/preseason/finance consequences.

## Protection and current limitations

Canonical/query connections use SQLite `mode=ro`, `query_only=ON` and an authorizer that denies writes, attachments and unsafe PRAGMAs. All original 64 user tables, the schema and 331 completed main-table fixtures retain their frozen fingerprints. The 046C profile permits only a specific independently replayed migration on a scratch copy. Tests that exercise corruption modify independent temporary copies only.

Original 046 warnings include 20 overdue cup ties, missing August payroll, stale objectives and inherited history quality gaps. Both candidate revisions settle August's R$1.38m payment, accrue **R$1,559,000.01** for September without a cash debit, and reconcile cup objectives. Cash is **R$30.55m**; fee authority **R$1.4m**, annual wage commitments **R$21.66m**, emergency reserve **R$16m** remain unchanged. The v2 profile also proves all 331 completed fixture rows unchanged while permitting only exact logged scheduled kickoff changes. Historical data-quality warnings remain.

See the [Task 02B report](docs/task02b_report.md), [Phase 2 engine design](docs/phase2_engine_design.md), [historical Phase 1 report](docs/phase1_report.md), [checkpoint format](docs/checkpoints.md), [payroll policy](docs/payroll_policy.md), [canonical history](docs/canonical_history.md), and [roadmap](docs/roadmap.md).

No matches have been simulated and no fictional dates advanced. Candidate 046C has not been promoted.
