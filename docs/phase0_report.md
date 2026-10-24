# Phase 0 completion report

Implemented on feature branch **`codex/phase-0-foundation`**. Work stops before Phase 1. No matches were simulated, no fictional dates advanced, no canonical bytes changed, and no 046C/047 generated. The original ZIP and its nested original backup chain are preserved.

## Verified canonical state and checksums

- **Save 046**, fictional **2027-09-26 23:30**; board confidence **61/100**; manager counter **45**.
- **Vasco 3–2 Palmeiras**, September 26, R25, fixture 322, already final. Carlos Vinícius equalized at 78; Johan Rojas entered and scored at 82, with substitution first in database ID order.
- **20 league clubs; 250 completed / 130 scheduled matches**. Every round contains ten games and 20 distinct clubs; all 20 standings reconcile from results.
- Vasco **ninth**, **38 points**, **25 played**, **11W 5D 9L**, **36 GF / 37 GA**.
- Next Vasco fixture: **Mirassol vs Vasco, October 3, 2027, 16:00, R26**, unplayed.
- Vasco eliminated from Carioca (semifinal), Sudamericana (Group A third, six points) and Copa do Brasil (R16, Fluminense 4–3 aggregate).
- 547 player records, nine transfers, 96 final Libertadores group matches, 96 final Sudamericana group matches and 48 completed CDB legs. Original verifier and manifest verification passed, including database equality with the nested original Save046 ZIP.
- Restricted cash **R$31.93m**, unreconciled for August payroll. Remaining authority: acquisition fees **R$1.4m**; annual incremental wages **R$0.34m**; agents/scouting **R$2.19m**. Restricted emergency reserve **R$16m**.

```text
Original ZIP SHA256:
527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719

Canonical database SHA256:
de58ac7f7942ef6048f002312cdc90314b26dc06a9853a59acaab1d5f88f4b28

Completed main-table fixture snapshot SHA256:
edb9ae71410c83c6c2c09a501af6022cf2263a8901bd1faa7dba03e4068ff639
```

ZIP/database hashes were checked again after implementation and tests and remained identical. The 331-row completed fixture snapshot covers all final main-table records, including 2026 and other domestic history. Additional continental/cup history is protected through all-table fingerprints.

## Architecture and files

- `pyproject.toml`: installable Python 3.11+ package, console entry point, no runtime dependencies; pytest development extra.
- `tools/bootstrap_handoff.py`: pinned-ZIP and manifest validation; path-safe, reproducible extraction; refuses modified destination files. Original extracted content remains ignored under `data/handoff/`.
- `braga_era/`: portable configuration, protected read-only SQLite access, state queries, stable history hashing, structured reusable audits, text/JSON CLI.
- `braga_era/baselines/save046.json`: fixed ZIP/DB/schema hashes, fingerprints for all 64 user tables, complete snapshot/hash of 331 final main-table fixtures. No baseline regeneration CLI.
- `tests/`: checkpoint/state tests, write-denial and path escaping, extraction safety/idempotency, temporary-copy corruption detection, original verification and installed CLI portability.
- `README.md`, root `AGENTS.md`, `.gitignore`, `.github/workflows/phase0.yml`: usage, durable engineering rules, local artifact exclusions and Windows/Linux Python 3.11–3.13 CI configuration.
- `docs/`: canonical provenance/history, architecture, schema guide plus exact DDL inventory, known issues and staged roadmap.
- `docs/validation/save046_audit.json` and `save046_inspect.json`: actual machine-readable audit and inspection captured from read-only queries.

## Commands

Create/activate a Python 3.11+ virtual environment, then run from the repository:

```sh
python -m pip install -e ".[dev]"
python tools/bootstrap_handoff.py
python -m braga_era inspect
python -m braga_era audit
python -m pytest
```

The prepared Windows environment can be used directly:

```powershell
.\.venv\Scripts\python.exe -m braga_era inspect
.\.venv\Scripts\python.exe -m braga_era audit
.\.venv\Scripts\python.exe -m pytest --basetemp .tmp/pytest
```

Both commands accept `--db PATH` and `--json`. `BRAGA_ERA_DB` supplies an environment default. `braga-era` is the installed executable. Audit returns 0 for preserved Save046 plus documented warnings, 1 for failed checks (or any warning under `--strict`), and 2 for input/open/query errors. Strict mode intentionally fails on inherited issues.

To re-extract for restoration review, use a fresh folder with `python tools/bootstrap_handoff.py --destination PATH`, then run the original verifier in that folder and `python -m braga_era audit --db PATH/canonical/braga_save.sqlite`. Never overwrite a changed handoff in place.

## Actual validation results

Environment: **Windows, Python 3.12.14, pytest 9.1.1**. The default Windows `python` alias was unavailable; the app's bundled Python created a local `.venv`. Temporary/build files stayed in ignored `.tmp/`. Pytest/build dependencies were installed into the project environment; production code needs only the standard library.

| Validation | Actual result |
|---|---|
| Original `data/handoff/tools/verify_handoff.py` | PASS, including original nested ZIP equality and entire manifest |
| `python -m braga_era inspect` | Correct version, date, next fixture, standings, cup progress and finance output |
| `python -m braga_era audit` | **27 checks, zero failures, 10 inherited warnings** |
| Full automated suite | **41 passed in 5.67 seconds**, after correcting Windows ZIP-name normalization handling |
| Installed CLI from an unrelated temporary working directory | Inspect/audit JSON succeed; strict audit returns 1; covered in automated suite |
| Deliberately modified temporary database copies | All 13 tampering scenarios detected; originals' hashes retained |
| Read-only defense | Eight write/attach/PRAGMA/transaction attempts rejected; database unchanged |
| Ordinary wheel build | PASS; bundled historical baseline verified in wheel |
| Wheel installed in an isolated target directory | Inspect/audit succeed outside repository; confirmed imports resolve to wheel files |
| Source whitespace check | `git diff --check` clean |

CI configuration was added; remote CI and other Python/OS combinations have not been executed locally. No claim of historical engine replay is made.

## Limitations and risks

See [known issues](known_issues.md) for evidence and exact query scope. These are inherited warnings, not repairs performed by Phase 0:

1. **20 overdue unplayed ties**: eight Libertadores R16, eight Sudamericana playoffs, four CDB QFs.
2. **August payroll missing**, September policy unresolved; ledger cash is not fully reconciled spending capacity.
3. **Six objective flags pending**, including settled competitions; Finance objective wording retains obsolete R$55m cap despite recorded R$68m authorization. Older meta notes also lag structured tables.
4. **2026 granular history partial**, with 71 league fixtures; final 20-team standings archive remains authoritative for final positions.
5. **39 completed main-table fixtures lack ISO dates**; no guessed dates inserted.
6. **22 cards after recorded starter exit minute**; full historical event quality is not proven by present checks.
7. **169 of 170 audit rows have empty/zero prematch xG**; 80 completed league games have no audit row. Historical reproducibility inputs are incomplete.
8. Archived Savarino **#196** and active **#354** both now reference Fluminense's club ID. Archive name and resolution table must govern eligibility; no identity merging or historical reassignment.
9. Legacy scripts perform top-level writes, depend on absolute paths and patch executable source text. They were inspected, never imported/executed.
10. Original `results046.json` reverses Rojas' same-minute substitution/goal presentation; database and episode preserve the correct sequence. Original JSON remains unchanged.

The audit deliberately validates a fixed Save046 baseline. A later approved save needs a new profile with controlled administrative deltas. File hashes detect byte changes; logical hashes explain data changes but cannot certify that inherited records were complete or semantically perfect. SQLite's declared foreign keys cover only part of the legacy schema. Versioned save promotion/restoration tooling, a new engine and a dashboard are later milestones.

## Proposed Phase 1 boundary

Create a separate candidate **046C** from the authenticated 046 parent; record parent/output hashes and a complete administrative log. Reconcile and reschedule unfinished cup ties with rest, travel, league and round-order checks. Reconcile August payroll and define September policy using actual contracts and idempotent periods, preserving restrictions and avoiding duplicate annual/cash charges. Resolve settled objective flags and stale budget wording with evidence.

Allow only reviewed administrative changes, preserve every completed sporting record and historical identity, validate before promotion, and test restoration. **No matches or calendar advancement belong in this proposed administrative checkpoint.** Phase 1 has not begun. Further milestones are detailed in [roadmap](roadmap.md).
