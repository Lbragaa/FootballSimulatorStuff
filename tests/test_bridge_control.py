"""Real lineage authorization on temporary TEST-ONLY registries; no match draws."""

import json
from uuid import uuid4
import pytest

from braga_era import lineage
from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN, otp
from braga_era.bridge.career import Career
from braga_era.bridge.control import Controls, PROFILE, OPERATIONS
from braga_era.db import file_sha256
from braga_era.history import digest

KEY = b"task04c-control-test-signing-key-ONLY"
SECRET = b"task04c-public-authenticator-test-only"


@pytest.fixture
def controls(tmp_path, accepted_path):
    registry = tmp_path / "authority.sqlite"
    lineage.provision(registry, KEY, test_only=True, commissioner="TEST-HUMAN", career_id="task04c-test", seed="fixed-test-seed")
    career = Career(registry, KEY, "task04c-test", True)
    career.root_parent = accepted_path
    now = [1700000000]
    gate = HumanGate(tmp_path / "gate.sqlite", KEY, SECRET,
                     {"profile": HUMAN, "career": career.career, "test_only": True,
                      "repository_id": 1436541980, "human_id": 78325376, "human_login": "Lbragaa"},
                     clock=lambda: now[0])
    gate.initialize()
    with lineage.access(registry, KEY) as (c, t):
        policy = {"profile": PROFILE, "action": "approve_remote_control_policies", "career": career.career,
                  "test_only": True, "authority_key_sha256": t["key_hash"],
                  "policy_sha256": digest(json.loads(t["policy_json"])), "repository_id": 1436541980,
                  "human_id": 78325376, "human_login": "Lbragaa", "operations": OPERATIONS}
    receipt = tmp_path / "policy.json"
    receipt.write_text(json.dumps(lineage.signed(policy, KEY)))
    controls = Controls(career, tmp_path / "control.sqlite", tmp_path / "executions", receipt, gate, enabled=True)
    controls.initialize()
    controls.now = now
    return controls


def approval(controls, ch, comment_id=1):
    return {"id": comment_id, "user": {"id": 78325376, "login": "Lbragaa"},
            "created_at": "2026-10-28T05:00:00Z", "updated_at": "2026-10-28T05:00:00Z",
            "body": ch["confirmation_format"].replace("<authenticator-code>", otp(SECRET, controls.now[0] // 30))}


def test_prepare_and_exact_separate_human_authorization(controls):
    original = file_sha256(controls.career.root_parent)
    pid = str(uuid4())
    summary = controls.prepare(pid, "2027-09-30 23:59")
    assert len(summary["fixtures"]) == 16
    assert summary["obligations"] == ["payroll:2027-09"]
    assert controls.prepare(pid, "2027-09-30 23:59") == summary
    assert controls.career.identity()["checkpoint"] == lineage.ROOT
    with pytest.raises(ValueError):
        controls.request_confirmation("execute_batch", pid, str(uuid4()), 6)
    with pytest.raises(ValueError):
        controls.perform(controls.statement("authorize_batch", pid), {})
    ch = controls.request_confirmation("authorize_batch", pid, str(uuid4()), 6)["confirmation"]
    result = controls.gate.confirm(ch["challenge_id"], 6, approval(controls, ch), controls.perform)
    assert result["execution_authorized"] and not result["executed"]
    assert controls.gate.resume(ch["challenge_id"], controls.perform) == result
    manifest = controls.manifest(pid)
    with lineage.access(controls.career.registry, KEY) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 1
        assert c.execute("SELECT state FROM batches").fetchone()[0] == "authorized"
        assert c.execute("SELECT count(*) FROM fixture_claims").fetchone()[0] == 16
        assert c.execute("SELECT count(*) FROM accepted").fetchone()[0] == 0
    assert file_sha256(controls.career.root_parent) == original
    assert controls.career.identity()["checkpoint"] == lineage.ROOT
    # Execution gets a DIFFERENT challenge; authorization alone never executes.
    run = controls.request_confirmation("execute_batch", pid, str(uuid4()), 7)
    assert run["confirmation"]["target_sha256"] == summary["manifest_sha256"]
    with pytest.raises(ValueError):
        controls.request_confirmation("accept_candidate", pid, str(uuid4()), 8)


def test_control_refuses_missing_policy_disabled_mode_and_tampering(controls):
    controls.enabled = False
    with pytest.raises(ValueError):
        controls.prepare(str(uuid4()), "2027-09-30 23:59")
    controls.enabled = True
    receipt = json.loads(controls.policy_receipt.read_text())
    receipt["document"]["test_only"] = False
    controls.policy_receipt.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        controls.prepare(str(uuid4()), "2027-09-30 23:59")


def test_competing_preparations_cannot_replace_authorized_seed(controls):
    first, second = str(uuid4()), str(uuid4())
    controls.prepare(first, "2027-09-30 23:59")
    controls.prepare(second, "2027-09-30 23:59")
    ch = controls.request_confirmation("authorize_batch", first, str(uuid4()), 6)["confirmation"]
    controls.gate.confirm(ch["challenge_id"], 6, approval(controls, ch), controls.perform)
    with pytest.raises(ValueError, match="claimed"):
        controls.request_confirmation("authorize_batch", second, str(uuid4()), 7)
    # Refusing the competing preparation must not strand the original batch.
    controls.request_confirmation("execute_batch", first, str(uuid4()), 8)
    with lineage.access(controls.career.registry, KEY) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM parent_claims").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM accepted").fetchone()[0] == 0
