"""Isolated controller rehearsal with SIMULATED consent, never phone evidence.

Only TEST-ONLY registries and public test enrollment are supported. No GitHub
credential, canonical registry, official key or existing authority is used.
"""

import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from braga_era import lineage
from braga_era.bridge.approval import HumanGate, PROFILE as HUMAN, otp
from braga_era.bridge.career import Career
from braga_era.bridge.control import Controls, PROFILE, OPERATIONS
from braga_era.bridge.roundup import Roundups
from braga_era.db import file_sha256
from braga_era.history import digest

KEY = b"TASK04C-PUBLIC-SIMULATED-TEST-KEY-ONLY"
SECRET = b"TASK04C-PUBLIC-SIMULATED-TOTP-ONLY"
SEED = "task04c-control-rehearsal-fixed-v1"


def identifier(name):
    return str(uuid5(NAMESPACE_URL, "braga-task04c-test-only:" + name))


def run(db, output, resume=False):
    db, output = Path(db).resolve(), Path(output).resolve()
    if file_sha256(db) != lineage.ROOT or (output.exists() and not resume) or (resume and not output.is_dir()):
        raise ValueError("Exact accepted parent and NEW test output, or explicit original --resume required")
    output.mkdir(parents=True, exist_ok=resume)
    registry = output / "authority.sqlite"
    if not resume:
        lineage.provision(registry, KEY, test_only=True, commissioner="SIMULATED-TEST-HUMAN",
                          career_id="task04c-local-controller-rehearsal", seed=SEED)
    career = Career(registry, KEY, "task04c-local-controller-rehearsal", True)
    career.root_parent = db
    now = [1700000000]
    gate = HumanGate(output / "human-gate.sqlite", KEY, SECRET,
                     {"profile": HUMAN, "career": career.career, "test_only": True,
                      "repository_id": 1436541980, "human_id": 78325376, "human_login": "Lbragaa"},
                     clock=lambda: now[0])
    if not resume:
        gate.initialize()
    with lineage.access(registry, KEY) as (c, t):
        receipt = {"profile": PROFILE, "action": "approve_remote_control_policies",
                   "career": career.career, "test_only": True, "authority_key_sha256": t["key_hash"],
                   "policy_sha256": digest(json.loads(t["policy_json"])), "repository_id": 1436541980,
                   "human_id": 78325376, "human_login": "Lbragaa", "operations": OPERATIONS}
    policy_path = output / "SIMULATED-policy-approval.json"
    if not resume:
        policy_path.write_text(json.dumps(lineage.signed(receipt, KEY)), encoding="utf-8")
    controls = Controls(career, output / "controls.sqlite", output / "executions", policy_path, gate, enabled=True)
    if not resume:
        controls.initialize()
    preparation = identifier("prepare-first-batch")
    summary = controls.prepare(preparation, "2027-09-30 23:59")
    assert len(summary["fixtures"]) == 16 and summary["obligations"] == ["payroll:2027-09"]

    def confirm(action, issue):
        now[0] += 30
        ch = controls.request_confirmation(action, preparation, identifier(action), issue)["confirmation"]
        comment = {"id": 900000 + issue, "user": {"id": 78325376, "login": "Lbragaa"},
                   "created_at": "2026-10-28T00:00:00Z", "updated_at": "2026-10-28T00:00:00Z",
                   "body": ch["confirmation_format"].replace("<authenticator-code>", otp(SECRET, now[0] // 30))}
        return gate.confirm(ch["challenge_id"], issue, comment, controls.perform)

    if resume:
        authorized = gate.resume(identifier("authorize_batch"), controls.perform)
        candidate = gate.resume(identifier("execute_batch"), controls.perform)
        accepted = gate.resume(identifier("accept_candidate"), controls.perform)
    else:
        authorized = confirm("authorize_batch", 100)
    assert authorized["execution_authorized"] and not authorized["executed"]
    if not resume:
        assert career.identity()["checkpoint"] == lineage.ROOT
    execute = lineage.execute
    try:
        def interrupted(*args, **kwargs):
            return execute(*args, **kwargs, crash="after_archive")
        lineage.execute = interrupted if not resume else execute
        try:
            if not resume:
                confirm("execute_batch", 101)
        except lineage.InjectedCrash:
            pass
        else:
            if not resume:
                raise AssertionError("Expected execution interruption")
    finally:
        lineage.execute = execute
    with lineage.access(registry, KEY) as (c, t):
        assert c.execute("SELECT state FROM batches").fetchone()[0] == ("accepted" if resume else "executing")
    # New controller/gate objects stand in for a restarted Python process.
    restarted_gate = HumanGate(gate.path, KEY, SECRET,
                              {k: v for k, v in gate.context.items() if k != "authenticator_sha256"},
                              clock=lambda: now[0])
    controls.gate = restarted_gate
    candidate = restarted_gate.resume(identifier("execute_batch"), controls.perform)
    assert candidate["independently_verified"]
    if not resume:
        assert career.identity()["checkpoint"] == lineage.ROOT  # execution did not accept.
    accept = lineage.accept
    try:
        def interrupted_accept(*args, **kwargs):
            return accept(*args, **kwargs, crash="after_accept_commit")
        lineage.accept = interrupted_accept if not resume else accept
        try:
            if not resume:
                confirm("accept_candidate", 102)
        except lineage.InjectedCrash:
            pass
        else:
            if not resume:
                raise AssertionError("Expected interrupted acceptance publication")
    finally:
        lineage.accept = accept
    accepted = restarted_gate.resume(identifier("accept_candidate"), controls.perform)
    assert accepted["accepted"] and accepted["test_only"]
    assert restarted_gate.resume(identifier("accept_candidate"), controls.perform) == accepted
    head = career.identity()["checkpoint"]
    group = career.play("next")["events"]
    keys = sorted(f["key"] for f in group)
    assert len(keys) == 16
    held = keys[0]
    preview = career.preview(held)
    assert not preview["postmatch_available"]
    page = career.play("narrate", held, page_id="task04c-detailed-first-page")
    assert not page["postmatch_available"]
    roundup = Roundups(career, output / "roundup-journal")
    response = roundup.run(identifier("roundup-others"), head, keys[1:], detailed=[held])
    assert len(response["summaries"]) == 15 and response["held_for_detail"] == [held]
    assert roundup.run(identifier("roundup-others"), head, keys[1:], detailed=[held]) == response
    assert [f["key"] for f in career.play("next")["events"]] == [held]
    for i in range(256):
        page = lineage.gameplay(registry, KEY, "narrate", held, 20, page_id=f"task04c-detail-completion:{i}")
        if page["postmatch_available"]:
            break
    else:
        raise AssertionError("Detailed match never reached final whistle")
    new_conversation = Career(registry, KEY, career.career, True)
    assert new_conversation.identity()["checkpoint"] == head
    assert lineage.gameplay(registry, KEY, "narrate", held, 20,
                            page_id=f"task04c-detail-completion:{i}") == page
    with lineage.access(registry, KEY) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM accepted").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM fixture_claims").fetchone()[0] == 16
        cursors = c.execute("SELECT count(*) FROM cursors").fetchone()[0]
    assert cursors == 16 and file_sha256(db) == lineage.ROOT
    report = {"scope": "NONCANONICAL DEVELOPMENT TEST", "human_approvals": "SIMULATED ONLY",
              "phone_or_github_roundtrip": False, "production_binding": False,
              "manifest_sha256": summary["manifest_sha256"], "candidate": candidate,
              "accepted": accepted, "executed_fixtures": 16, "payroll_obligations": 1,
              "execution_crash": "after_archive", "acceptance_crash": "after_accept_commit",
              "roundup_fixtures": 15, "detailed_held_fixtures": 1, "revelation_cursors": cursors,
              "same_page_replayed": True, "accepted_root_unchanged": True,
              "next_events": new_conversation.play("next")["events"]}
    (output / "rehearsal.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"candidate", "accepted", "next_events"}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Resume this exact TEST authority; never reset its seed/cursor")
    args = parser.parse_args()
    run(args.db, args.output, args.resume)
