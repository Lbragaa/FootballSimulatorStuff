from copy import deepcopy
import json
from uuid import uuid4
import pytest
from braga_era.bridge.worker2 import Worker2
from braga_era.bridge.roundup import expand_events
from braga_era.bridge.approval import otp
from braga_era import lineage
from test_bridge import Transport, Career, REQUESTERS, request
from test_bridge_control import controls, approval


def req(career, command, sequence, **args):
    r = request(command, sequence=sequence, **args)
    return {**r, "protocol": "braga-bridge-2", "career": career.career,
            "expected_checkpoint": career.identity()["checkpoint"]}


def users():
    people = deepcopy(REQUESTERS)
    people["78325376"]["scopes"].append("control")
    return people


def test_missing_controls_do_not_block_reading(tmp_path):
    transport, career = Transport(), Career()
    w = Worker2(transport, career, tmp_path / "ledger.sqlite", users())
    issue = transport.add(req(career, "inspect_career", 1))
    assert w.poll()["next_sequence"] == 2
    assert transport.result(issue)["response"]["result"]["career"] == career.career
    issue = transport.add(req(career, "prepare_control_batch", 2, until="2027-09-30 23:59"))
    w.poll()
    assert transport.result(issue)["response"]["status"] == "refused"
    assert not w.capabilities()["execution_enabled"]


def test_compact_narration_reconstructs_original_pages_and_replays(tmp_path):
    transport, career = Transport(), Career()
    original_play = career.play
    def play(view, fixture=None, page_id=None):
        page = original_play(view, fixture, page_id)
        if view == "narrate":
            for event in page["events"]:
                event["on_field_home"], event["on_field_away"] = [1, 2], [3, 4]
        return page
    career.play = play
    w = Worker2(transport, career, tmp_path / "ledger.sqlite", users())
    r = req(career, "narrate_count", 1, fixture="league:1", count=3)
    n = transport.add(r)
    w.poll()
    public = transport.result(n)["response"]["result"]
    assert len(public["on_field_states"]) == 1
    expanded = expand_events({"presentation": public["presentation"],
                              "events": [e for p in public["pages"] for e in p["events"]],
                              "on_field_states": public["on_field_states"]})
    assert all(e["on_field_home"] == [1, 2] for e in expanded)
    assert career.position == 3
    duplicate = transport.add(r)
    w.poll()
    assert transport.result(duplicate) == transport.result(n) and career.position == 3


def prepared_worker(tmp_path, controls, crash=None):
    transport = Transport()
    w = Worker2(transport, controls.career, tmp_path / "ledger.sqlite", users(), controls=controls, crash=crash)
    prep_request = req(controls.career, "prepare_control_batch", 1, until="2027-09-30 23:59")
    prep_issue = transport.add(prep_request)
    w.poll()
    preparation = transport.result(prep_issue)["response"]["result"]
    auth = req(controls.career, "request_authorize_batch", 2,
               preparation_id=preparation["preparation_id"], manifest_sha256=preparation["manifest_sha256"])
    issue = transport.add(auth)
    w.poll()
    return transport, w, issue, transport.result(issue)["response"]["result"]["confirmation"]


@pytest.mark.parametrize("crash", ["after_control_effect", "after_control_post"])
def test_issue_alone_never_authorizes_and_crash_resumes_receipt(tmp_path, controls, crash):
    transport, worker, issue, challenge = prepared_worker(tmp_path, controls, crash=crash)
    with lineage.access(controls.career.registry, controls.career.key) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 0
    transport.notes[issue].append(approval(controls, challenge, 500))
    with pytest.raises(RuntimeError):
        worker.poll()
    restarted = Worker2(transport, controls.career, worker.path, users(), controls=controls)
    restarted.poll()
    restarted.poll()
    receipts = [x for x in transport.notes[issue] if x["body"].startswith("BRAGA_CONTROL_RECEIPT_V2")]
    assert len(receipts) == 1
    doc = json.loads(receipts[0]["body"].split("```json\n")[1].split("\n```", 1)[0])
    assert lineage.check_signed(doc, controls.career.key)["result"]["execution_authorized"]
    with lineage.access(controls.career.registry, controls.career.key) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 1
        assert c.execute("SELECT state FROM batches").fetchone()[0] == "authorized"
        assert c.execute("SELECT count(*) FROM accepted").fetchone()[0] == 0


def test_invalid_confirmation_is_not_retried_each_poll(tmp_path, controls):
    transport, worker, issue, challenge = prepared_worker(tmp_path, controls)
    bad = approval(controls, challenge, 500)
    valid = bad["body"].rsplit(" ", 1)[1]
    bad["body"] = bad["body"].rsplit(" ", 1)[0] + f" {(int(valid)+123)%1000000:06}"
    transport.notes[issue].append(bad)
    worker.poll()
    count = len(transport.notes[issue])
    worker.poll()
    assert len(transport.notes[issue]) == count
    transport.notes[issue].append(approval(controls, challenge, 501))
    worker.poll()
    assert any(x["body"].startswith("BRAGA_CONTROL_RECEIPT_V2") for x in transport.notes[issue])


def test_control_scope_revocation_before_confirmation_preserves_authority(tmp_path, controls):
    transport, worker, issue, challenge = prepared_worker(tmp_path, controls)
    transport.notes[issue].append(approval(controls, challenge, 500))
    people = users()
    people["78325376"]["scopes"].remove("control")
    Worker2(transport, controls.career, worker.path, people, controls=controls).poll()
    with lineage.access(controls.career.registry, controls.career.key) as (c, t):
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 0
