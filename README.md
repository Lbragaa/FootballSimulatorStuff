# THE BRAGA ERA

One continuous fictional football universe, preserved at **Save 046**. Phase 0 provides portable, read-only inspection and auditing. Python 3.11+; no runtime dependencies or external services.

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

Audit exit codes: **0** = checkpoint preserved (inherited warnings still listed); **1** = failed invariant, or warnings under `--strict`; **2** = input/open/query error. `audit --strict` intentionally exits 1 on unmodified Save 046. This audit targets Save 046 specifically; a later save needs a separately reviewed validation profile.

## Protection and current limitations

Connections use SQLite `mode=ro`, `query_only=ON` and an authorizer that denies writes, attachments and unsafe PRAGMAs. All 64 user tables, the schema and all 331 completed main-table fixtures have checked-in fingerprints. The audit also independently checks league scheduling, standings, R25 goals/shots/appearances, player identities and finance limits. It never repairs the database. Tests that exercise corruption modify independent temporary copies only.

Known warnings include **20 overdue unplayed cup ties**, missing August payroll, pending September policy, stale objective flags, partial 2026 fixture coverage, missing historical dates, historical card timing, incomplete engine metrics, Savarino's archived identity and JSON event ordering. Restricted cash **R$31.93m** is unreconciled; acquisition authority remaining is **R$1.4m**. See [known issues](docs/known_issues.md).

See the [Phase 0 report](docs/phase0_report.md), [canonical history and checksums](docs/canonical_history.md), [architecture](docs/architecture.md), [schema guide](docs/schema.md), [exact schema inventory](docs/schema_inventory.md), and [roadmap](docs/roadmap.md).

No matches have been simulated, no fictional dates advanced, and no new saves created by this project.
