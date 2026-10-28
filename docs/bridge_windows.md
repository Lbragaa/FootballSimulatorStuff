# One-time Windows worker setup

Ordinary play needs only ChatGPT + GitHub on the phone, and a powered-on online
PC running this Python worker. No Codex process, OpenAI API, Actions simulation
runner, terminal or dashboard is part of ordinary play. Initial installation,
credential storage, recovery and optional startup enablement are local setup.

Use Python 3.11–3.13 and install this branch/release in a stable environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m braga_era.bridge --help
```

For a permanent startup installation, install the reviewed wheel in a stable
environment outside a working checkout; do not switch branches beneath a running
editable installation. Runtime uses the Python standard library only.

## Private credential

GitHub Settings → Developer settings → Personal access tokens → Fine-grained
tokens. Select owner `Lbragaa`, **only** `BragaEraCommandBridge`, an expiry, Issues
read/write and Metadata read-only. Do not add Contents, Actions or administration
permissions. Create it yourself and enter it only at the local hidden prompt:

```powershell
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json credential-set
```

Never paste it into ChatGPT, issues, command-line arguments or configuration JSON.
It is stored in Windows Credential Manager under
`BragaEraBridge/1436541980/github`. The worker rejects broad classic/OAuth tokens.
Fine-grained permissions are documented by [GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
The prefix check is not proof of the token's selected repositories: the human
must review the actual token grant. Rotate/revoke it at GitHub when needed.

## Local configuration and start

Keep configuration, ledger and existing authority paths local. The prepared
`output/task04b-test/config.json` binds only the disposable TEST-ONLY career.
Configuration contains local paths and credential **target name**, never a token.
No request can change these paths. Restrict the directory to the Windows account
running the worker. The existing commissioner key remains local; the test key
is explicitly public dummy material and cannot be promoted to production.

```powershell
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json status
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json once
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json run
```

The last command keeps polling until stopped. Network/rate-limit errors leave
requests queued and retry without replacing IDs, seeds or narration pages. A
credential/configuration integrity failure stops rather than silently rebinding
another authority. On restart use the same config and ledger. Do not delete
request receipts or change the career seed to recover.

For a hidden manual launch after credential setup, from the repository folder:

```powershell
$ConfigPath = (Resolve-Path output/task04b-test/config.json).Path
Start-Process -FilePath "$PWD\.venv\Scripts\pythonw.exe" -ArgumentList @('-m','braga_era.bridge','--config',('"'+$ConfigPath+'"'),'run') -WorkingDirectory $PWD -WindowStyle Hidden
```

Keep one worker per ledger/authority. The OS process lock rejects concurrent
runners. Finish/stop bridge processing before an out-of-band authorized execution,
acceptance or authority transfer; then restart with its updated accepted head.
For a genuinely new configuration, initialize its ledger once with the local
`initialize-ledger` action before `run`/`once`. The supplied TEST configuration
is already initialized. A missing ledger on restart is refused: restore its
backup rather than silently starting a new sequence. Existing ledgers are never
reset by the initialization command.

## Explicit login startup opt-in

Nothing enables startup automatically. Once the human explicitly chooses it:

```powershell
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json startup-enable --confirm-login-startup
```

This registers `BragaEraBridge-1436541980` in Windows Task Scheduler, at the
current user's login, least privilege, without a stored Windows password. It
runs `pythonw`, ignores duplicate instances and restarts after failure. Review
the task in Task Scheduler. It does not wake or prevent sleep. An existing task
is not overwritten. To remove it explicitly:

```powershell
.\.venv\Scripts\python.exe -m braga_era.bridge --config output/task04b-test/config.json startup-disable --confirm-login-startup
```

Sleep pauses processing; commands remain in GitHub. After wake/network recovery
polling resumes. A reboot requires user login for this optional task. While the
PC is off/asleep, Hikari must report “queued”, not invent an engine answer. Test
an actual sleep/reboot after enabling startup; process-restart tests alone are
not proof of physical Windows login behavior.

## Backups and later production/cloud binding

Back up the bridge ledger with the existing accepted-career/authority handoff,
only when the worker is stopped. Keep encrypted commissioner-key recovery backups
separately; never upload the ledger, keys or saves to the command repository.
Ordinary ChatGPT receives only minimal worker replies. Do not activate two
restored ledger/authority copies.

No production authority is provisioned here. After separate approval, a trusted
operator can point a new local config to an already-approved production registry
and its local key, set `test_only=false` and explicitly approve that binding.
Mode mismatch and a false `production_binding_approved` are rejected. Heavy
execution/acceptance commands remain absent even then.

The processor/REST transport is platform-independent. A future Linux host can
run the same module with a secret manager supplying `BRAGA_BRIDGE_GITHUB_TOKEN`
and its own supervised service. No paid host is deployed by this task. Moving
the official key/authority requires the separately approved transfer/fencing
procedure; simply copying a TEST configuration is not migration authorization.
