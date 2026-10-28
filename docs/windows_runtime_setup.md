# Windows setup for Hikari — preparation only

This guide does not authorize gameplay. **Do not create a production key, commit
a career seed or provision an authority during the present task.** Sections 1–3
are safe preparation; section 4 describes work reserved for a later explicit
human instruction. Use one trusted Windows runtime and one writable career
authority. No server or dashboard is required.

## 1. Open the merged repository and check Python

Open PowerShell in your existing repository folder. With a clean working tree:

```powershell
git status --short
git switch main
git pull --ff-only origin main
git log -1 --format="%H %s"
py -0p
```

If there are local changes, keep them and resolve their disposition before pulling.
Use Python **3.11–3.13**. The commands below choose 3.12; substitute your installed
supported version. Create `.venv` only if it does not already exist:

```powershell
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -c "import sys, sqlite3, braga_era; print(sys.version); print(sqlite3.sqlite_version); print(braga_era.__version__)"
.\.venv\Scripts\python.exe -m braga_era.continuous --help
```

Expect package **0.7.0**. Activation and changing PowerShell execution policy are
unnecessary because every command calls the environment's Python explicitly.

## 2. Authenticate the accepted release

Install into a **fresh** directory, for example `output/accepted-046c`:

```powershell
.\.venv\Scripts\python.exe tools\bootstrap_accepted.py --download --output output/accepted-046c
.\.venv\Scripts\python.exe -m braga_era inspect --db output/accepted-046c/database.sqlite
.\.venv\Scripts\python.exe -m braga_era audit --db output/accepted-046c/database.sqlite
.\.venv\Scripts\python.exe -m braga_era save verify output/accepted-046c
(Get-FileHash output/accepted-046c/database.sqlite -Algorithm SHA256).Hash
```

If that directory already exists, inspect/audit/verify it; do not overwrite it.
Bootstrap authenticates the release ZIP and database and never promotes a save.
The DB hash must be
`27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`;
the accepted ZIP hash is
`df3c8820b4bb05df9af14359aa9f9aea4d67f68456701a08cecaad11438142e8`.
Stop on a mismatch. Expected historical warnings remain documented.
Inspection must show September 26 at 23:30 and Mirassol–Vasco unplayed.

## 3. Human chooses an independent backup location

Use an external drive or separately secured backup destination outside this
repository and its OneDrive folder. Another folder on the same disk is not an
independent backup. The human must supply the actual location and check access.
The example drive letter is a placeholder:

```powershell
$BackupRoot = 'E:\BragaEraBackup' # replace with your independently backed-up location
if (-not (Test-Path ([System.IO.Path]::GetPathRoot($BackupRoot)))) { throw 'Choose the actual backup drive first' }
if (Test-Path "$BackupRoot\046C-root") { throw 'Choose a fresh backup destination' }
New-Item -ItemType Directory -Path "$BackupRoot\046C-root" | Out-Null
Copy-Item -LiteralPath output/accepted-046c -Destination "$BackupRoot\046C-root\accepted-046c" -Recurse -ErrorAction Stop
Copy-Item -LiteralPath docs/acceptance/046C_v2_approval.json -Destination "$BackupRoot\046C-root\046C_v2_approval.json" -ErrorAction Stop
git rev-parse HEAD | Set-Content "$BackupRoot\046C-root\software-commit.txt"
```

Choose a fresh destination for each backup; do not overwrite an existing backup.
Compare the backed-up DB hash with the accepted hash above. Keep the immutable
original handoff ZIP too. After gameplay is separately authorized, use the
authority-aware `backup` command from the [runbook](continuous_play_runbook.md),
then copy its complete bundle to independent storage. Finish/recover any pending
batch first. A database alone omits authority claims and narration progress.

## 4. STOP: later human-authorized key and authority setup

**Instructions only; not performed by this preparation.** The human must first
review the [policy bundle](commissioner_policy_review.md) and give a separate
explicit production-setup instruction. Use a local directory outside Git and
OneDrive, for example `$env:LOCALAPPDATA\BragaEra\Production`.

After that future instruction, the trusted operator can create a new protected
secret directory, restrict its ACL to the signed-in Windows user and generate
32 random key bytes directly into a file. Never replace an existing key:

```powershell
# FUTURE AUTHORIZED SETUP ONLY — do not run as part of present preparation
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'BragaEra\Production'
$SecretDir = Join-Path $RuntimeRoot 'secrets'
if (Test-Path $SecretDir) { throw 'Existing secret directory: inspect/recover; do not regenerate a key' }
New-Item -ItemType Directory -Path $SecretDir | Out-Null
$Operator = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $SecretDir /inheritance:r /grant:r "${Operator}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Key-directory permission setup failed' }
$KeyFile = Join-Path $SecretDir 'commissioner.key'
$KeyBytes = New-Object byte[] 32
$Generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$Generator.GetBytes($KeyBytes)
$Generator.Dispose()
$KeyStream = [System.IO.File]::Open($KeyFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
try { $KeyStream.Write($KeyBytes, 0, $KeyBytes.Length); $KeyStream.Flush() }
finally { $KeyStream.Dispose(); [Array]::Clear($KeyBytes, 0, $KeyBytes.Length) }
```

Do not display the key, use `Get-Content` on it, commit it, attach it to ChatGPT,
put it in reports or include it in save archives. The human must arrange two
encrypted/offline key backups separately from routine save/authority handoffs.
Check recovery privately. Do not send the key to an assistant to “verify” it.

There is no production-init CLI. Later provisioning uses the existing explicit
Python API: `lineage.provision(registry_path, key_bytes, test_only=False,
commissioner=..., career_id=..., seed=...)`. The trusted operator reads key bytes
from the protected file locally. The human supplies the commissioner identity,
fresh career ID and once-only career seed in that later task. **No values are
chosen or committed here.** Keep the production registry outside the repository,
e.g. `$RuntimeRoot\authority\career.sqlite`. Do not convert a TEST-ONLY registry.

The human must then review and authorize the actual prepared September 30
manifest; provisioning or policy approval does not authorize execution. Follow
the exact prepare → authorize → execute → verify → separate accept commands in
the [continuous runbook](continuous_play_runbook.md).

## 5. ChatGPT handoff and a new conversation

The GitHub connector reads repository content; it cannot execute local Python or
update SQLite. The simplest setup keeps execution and the key on this Windows
machine. After a future authorized batch is separately accepted:

1. Run `continuous ... inspect` and `continuous ... play next` locally, using the
   registry/key **paths**, not secret values. Give Hikari the structured outputs.
2. Export a signed cursor with `continuous ... cursor-export --output cursor.json`
   and make an authority-aware backup bundle. The bundle includes the accepted
   checkpoint ZIP and signed acceptance/cursor, never the key. It contains sealed
   future results: only the trusted worker should inspect its private database.
3. If a ChatGPT Python environment is to hold the files, transfer that complete
   portable bundle and the installed package/version information. Keep the key
   on Windows; the remote environment cannot authenticate HMACs or run trusted
   authority commands without a separate trusted-runtime/key arrangement. Merely
   attaching the ZIP does not provide one. Prefer returning safe local command
   outputs to ChatGPT for ordinary narration.
4. On a new conversation, keep the same active local registry. Give Hikari the
   accepted checkpoint hash, signed cursor file, last page ID/output and this
   instruction: “Resume stored narration using this runtime. Do not reroll,
   reveal later events or treat this handoff as authority for new fixtures.”
5. Retry the same `play narrate --page-id ... --count ...` request if delivery was
   interrupted; it returns the saved page. Use a new page ID only for the next
   page. The registry retains the authoritative cursor; do not reset it or import
   an older cursor. Changing a chat does not require moving the authority.

An intentional runtime move uses `backup --transfer`, which fences the old writer,
then `restore-backup --production` on the one new trusted runtime. Restore the key
there through the human's private channel, never via chat or the archive. This is
a separate human operation; never activate two writable copies. Full details and
the copyable handoff are in the [runbook](continuous_play_runbook.md).
