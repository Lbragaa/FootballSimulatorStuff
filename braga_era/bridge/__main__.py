"""Local polling entry point. No OpenAI/Codex API or GitHub Actions execution."""

import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import sqlite3
import time
from .career import Career
from .github import GitHub, TransportError
from .worker import Worker
from . import credentials


def config(path):
    v = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "repository",
        "repository_id",
        "worker_id",
        "requesters",
        "registry",
        "key_file",
        "ledger",
        "career",
        "test_only",
        "credential_target",
        "poll_seconds",
        "production_binding_approved",
    }
    if set(v) - required - {"root_parent"} or not required <= set(v):
        raise ValueError("Bridge configuration fields")
    if (
        type(v["test_only"]) is not bool
        or type(v["production_binding_approved"]) is not bool
    ):
        raise ValueError("Explicit authority mode required")
    if not v["test_only"] and not v["production_binding_approved"]:
        raise ValueError("Production connection needs separate local approval")
    if type(v["poll_seconds"]) is not int or not 5 <= v["poll_seconds"] <= 300:
        raise ValueError("Polling interval")
    for name in ("repository_id", "worker_id"):
        if type(v[name]) is not int or v[name] <= 0:
            raise ValueError("Pinned numeric identity")
    for name in ("registry", "key_file", "ledger", "root_parent"):
        if name in v and not Path(v[name]).is_absolute():
            raise ValueError("Use absolute local paths")
    for identity, entry in v["requesters"].items():
        if (
            not identity.isdigit()
            or set(entry) != {"login", "scopes"}
            or not set(entry["scopes"]) <= {"read", "narration", "admin"}
        ):
            raise ValueError("Requester scope")
    return v


def build(v, token):
    career = Career(
        v["registry"], Path(v["key_file"]).read_bytes(), v["career"], v["test_only"]
    )
    if "root_parent" in v:
        career.root_parent = Path(v["root_parent"])
    transport = GitHub(v["repository"], v["repository_id"], v["worker_id"], token)
    return Worker(transport, career, v["ledger"], v["requesters"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument(
        "action",
        choices=(
            "run",
            "once",
            "credential-set",
            "status",
            "startup-enable",
            "startup-disable",
        ),
    )
    p.add_argument("--confirm-login-startup", action="store_true")
    a = p.parse_args(argv)
    try:
        v = config(a.config)
        if a.action.startswith("startup-"):
            if not a.confirm_login_startup:
                raise ValueError("Explicit startup confirmation required")
            from . import startup

            if a.action == "startup-enable":
                startup.enable(a.config, v["repository_id"])
            else:
                startup.disable(v["repository_id"])
            print("Startup configuration updated by explicit local request.")
            return 0
        if a.action == "credential-set":
            credentials.write(
                v["credential_target"],
                getpass.getpass(
                    "Fine-grained GitHub PAT (hidden; never paste into chat): "
                ),
            )
            print("Credential stored in Windows Credential Manager.")
            return 0
        if a.action == "status":
            career = Career(
                v["registry"],
                Path(v["key_file"]).read_bytes(),
                v["career"],
                v["test_only"],
            )
            print(
                json.dumps(
                    {
                        **career.identity(),
                        "execution_enabled": False,
                        "acceptance_enabled": False,
                    }
                )
            )
            return 0
        # Linux migration hook: secret manager supplies an environment credential.
        token = (
            credentials.read(v["credential_target"])
            if os.name == "nt"
            else os.environ["BRAGA_BRIDGE_GITHUB_TOKEN"]
        )
        if not token.startswith("github_pat_"):
            raise ValueError(
                "Persistent worker requires a repository-scoped fine-grained PAT"
            )
        worker = build(v, token)
        while True:
            try:
                result = worker.poll()
                if a.action == "once":
                    print(json.dumps(result))
                    return 0
            except (TransportError, RuntimeError):
                # Generic local status, no request bodies or secrets. Resume after network/sleep.
                if a.action == "once":
                    raise
            if a.action == "once":
                return 0
            time.sleep(v["poll_seconds"])
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, sqlite3.Error):
        print(
            "Bridge unavailable or refused configuration; inspect locally without publishing secrets.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
