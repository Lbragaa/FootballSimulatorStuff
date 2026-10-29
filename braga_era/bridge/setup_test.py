"""One-time TEST-ONLY phone rehearsal setup. Production setup is unsupported.

Enrollment must run in the human's interactive local terminal, never through
chat/tool output: it displays a private authenticator enrollment secret there.
"""

import argparse
import base64
import getpass
import json
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import urlencode

from .. import lineage
from ..db import file_sha256
from ..history import digest
from .__main__ import config, build
from .approval import HumanGate, PROFILE as HUMAN, otp
from .control import Controls, PROFILE, OPERATIONS

CAREER = "task04c-phone-test-v1"
SEED = "task04c-phone-rehearsal-fixed-v1"


def create(db, directory):
    db, directory = Path(db).resolve(), Path(directory).resolve()
    if file_sha256(db) != lineage.ROOT or directory.exists():
        raise ValueError("Exact accepted parent and NEW TEST directory required")
    directory.mkdir(parents=True)
    key_path = directory / "TEST-ONLY-signing.key"
    key = secrets.token_bytes(32)
    with key_path.open("xb") as f:
        f.write(key)
    registry = directory / "authority/career.sqlite"
    lineage.provision(registry, key, test_only=True, commissioner="Lbragaa-TEST-ONLY",
                      career_id=CAREER, seed=SEED)
    value = {"repository": "Lbragaa/BragaEraCommandBridge", "repository_id": 1436541980,
             "worker_id": 78325376, "requesters": {"78325376": {"login": "Lbragaa", "scopes": ["read", "narration", "admin", "control"]}},
             "registry": str(registry), "key_file": str(key_path),
             "ledger": str(directory / "bridge/ledger.sqlite"), "career": CAREER,
             "test_only": True, "root_parent": str(db), "protocol": "braga-bridge-2",
             "credential_target": "BragaEraBridge/1436541980/github", "poll_seconds": 15,
             "production_binding_approved": False,
             "control": {"enabled": False, "production_binding_approved": False,
                         "human_id": 78325376, "human_login": "Lbragaa",
                         "store": str(directory / "control/preparations.sqlite"),
                         "directory": str(directory / "executions"),
                         "policy_receipt": str(directory / "control/TEST-ONLY-policy.json"),
                         "human_gate": str(directory / "control/human.sqlite"),
                         "authenticator_file": str(directory / "control/TEST-ONLY-authenticator.key")}}
    path = directory / "config.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    build(config(path), "")  # Explicit NEW inbox; no GitHub call or match execution.
    print("Fresh TEST-ONLY authority/configuration created. No match authorized or executed.")
    return path


def enroll(path, confirmed=False):
    value = config(path)
    if not confirmed or value["test_only"] is not True or value.get("protocol") != "braga-bridge-2":
        raise ValueError("Explicit TEST-ONLY enrollment confirmation required")
    if not Path(value["ledger"]).is_file():
        raise ValueError("Missing established inbox; restore its backup, never reset it")
    worker = build(value, "")
    career = worker.career
    spec = value["control"]
    context = {"profile": HUMAN, "career": career.career, "test_only": True,
               "repository_id": value["repository_id"], "human_id": spec["human_id"],
               "human_login": spec["human_login"]}
    secret_path = Path(spec["authenticator_file"])
    gate_path = Path(spec["human_gate"])
    if spec["enabled"] and (not gate_path.is_file() or not Path(spec["store"]).is_file()):
        raise ValueError("Missing enrolled control journals; restore original private backups")
    if not gate_path.exists():
        if not sys.stdin.isatty():
            raise ValueError("Run enrollment in the human's interactive local console; never in chat")
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        if not secret_path.exists():
            with secret_path.open("xb") as f:
                f.write(secrets.token_bytes(20))
        secret = secret_path.read_bytes()
        code_key = base64.b32encode(secret).decode().rstrip("=")
        print("PRIVATE TEST-ONLY ENROLLMENT — do not copy this screen into chat or GitHub.")
        print("In your phone authenticator, add a time-based account named Braga TEST ONLY.")
        print("Setup key:", code_key)
        print("Manual setup: six digits, SHA1, 30 seconds.")
        print("Enrollment URI (local use only): otpauth://totp/Braga:TEST-ONLY?" +
              urlencode({"secret": code_key, "issuer": "Braga", "algorithm": "SHA1", "digits": 6, "period": 30}))
        entered = getpass.getpass("Enter its current six-digit TEST code here (hidden): ").strip()
        now = int(time.time()) // 30
        if not any(secrets.compare_digest(otp(secret, counter), entered) for counter in range(now-1, now+2)):
            raise ValueError("Authenticator verification failed; no control approval enabled")
        gate = HumanGate(gate_path, career.key, secret, context)
        gate.initialize()
    else:
        gate = HumanGate(gate_path, career.key, secret_path.read_bytes(), context)
        with gate.access():
            pass  # Resume interrupted local enrollment, never reset its counter.
    with lineage.access(career.registry, career.key) as (c, t):
        receipt = {"profile": PROFILE, "action": "approve_remote_control_policies",
                   "career": career.career, "test_only": True, "authority_key_sha256": t["key_hash"],
                   "policy_sha256": digest(json.loads(t["policy_json"])), "repository_id": value["repository_id"],
                   "human_id": spec["human_id"], "human_login": spec["human_login"], "operations": OPERATIONS}
    receipt_path = Path(spec["policy_receipt"])
    lineage.publish_json(receipt_path, lineage.signed(receipt, career.key))
    controls = Controls(career, spec["store"], spec["directory"], receipt_path, gate, enabled=True)
    if Path(spec["store"]).exists():
        with controls.access():
            pass
    else:
        controls.initialize()
    value["control"]["enabled"] = True
    temporary = Path(path).with_suffix(".pending")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print("TEST-ONLY authenticator verified and control review enabled. No match authorized or executed.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("create", "enroll"))
    p.add_argument("--db", type=Path)
    p.add_argument("--directory", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--confirm-test-enrollment", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.action == "create" and a.db and a.directory:
            create(a.db, a.directory)
        elif a.action == "enroll" and a.config:
            enroll(a.config, a.confirm_test_enrollment)
        else:
            raise ValueError("Explicit TEST setup arguments required")
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print("TEST setup not completed; inspect locally. Do not send enrollment secrets through chat.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
