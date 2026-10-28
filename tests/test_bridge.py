"""No football RNG needed to test transport retries, tampering and cursor control."""

import copy
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
import pytest
from braga_era.bridge.protocol import parse, schema, COMMANDS
from braga_era.bridge.worker import Worker, MARKER
from braga_era.history import canonical_json as encode

HEAD = "a" * 64
USER = {"id": 78325376, "login": "Lbragaa"}
REQUESTERS = {
    str(USER["id"]): {"login": USER["login"], "scopes": ["read", "narration", "admin"]}
}


def request(command="inspect_career", sequence=1, **args):
    return {
        "protocol": "braga-bridge-1",
        "request_id": str(uuid4()),
        "sequence": sequence,
        "career": "test-career",
        "expected_checkpoint": HEAD,
        "command": command,
        "args": args,
    }


class Transport:
    repository_id = 1436541980
    worker_id = 78325376

    def __init__(self):
        self.rows = {}
        self.notes = {}
        self.private = True
        self.offline = False
        self.lost_post = False

    def privacy(self):
        if not self.private or self.offline:
            raise RuntimeError("Unavailable")

    def add(self, r, actor=None, edited=None):
        n = len(self.rows) + 1
        self.rows[n] = {
            "number": n,
            "body": encode(r),
            "title": "[BRAGA] " + r["request_id"],
            "state": "open",
            "user": actor or USER,
            "bridge_last_edited_at": edited,
        }
        return n

    def issues(self):
        return [copy.deepcopy(r) for r in self.rows.values() if r["state"] == "open"]

    def issue(self, n):
        return copy.deepcopy(self.rows[n])

    def comments(self, n):
        return self.notes.get(n, [])

    def reply(self, n, body):
        self.notes.setdefault(n, []).append(
            {"id": len(self.notes.get(n, [])) + 1, "body": body, "user": USER}
        )
        if self.lost_post:
            self.lost_post = False
            raise RuntimeError("Network lost after successful POST")

    def close(self, n):
        self.rows[n]["state"] = "closed"

    def result(self, n):
        body = self.notes[n][-1]["body"]
        return json.loads(body.split("```json\n")[1].split("\n```", 1)[0])


class Career:
    career = "test-career"
    test_only = True
    key = b"TEST-ONLY-BRIDGE-KEY-NOT-PRODUCTION-12345"

    def __init__(self):
        self.head = HEAD
        self.pages = {}
        self.position = 0

    def identity(self):
        return {"checkpoint": self.head, "career": self.career, "test_only": True}

    def inspect(self):
        return {
            "career": self.career,
            "test_only": True,
            "accepted_checkpoint": self.head,
        }

    def play(self, view, fixture=None, page_id=None):
        if view == "next":
            return {
                "events": [{"key": "league:1"}],
                "official_execution_authorized": False,
            }
        if view == "table":
            return {"standings": [], "basis": "revealed finals only"}
        if fixture != "league:1":
            raise ValueError("Future private fixture")
        if page_id in self.pages:
            return self.pages[page_id]
        self.position += 1
        kind = {
            1: "KICK_OFF",
            2: "SHOT",
            3: "HALF_TIME",
            4: "SECOND_HALF",
            5: "FINAL_WHISTLE",
        }.get(self.position, "FINAL_WHISTLE")
        value = {
            "events": [{"sequence": self.position, "kind": kind}],
            "postmatch_available": self.position >= 5,
        }
        self.pages[page_id] = value
        return value

    def boundary_seen(self, fixture, boundary):
        return self.position >= (3 if boundary == "HALF_TIME" else 5)

    def preview(self, fixture, news=False):
        if fixture != "league:1":
            raise ValueError("Future fixture")
        return {"fixture_key": fixture, "postmatch_available": False}

    def prepare(self, until, request_id):
        return {"id": request_id, "until": until}

    def manifest_summary(self, m):
        return {"manifest_sha256": "b" * 64, "execution_authorized": False}


@pytest.fixture
def rig(tmp_path):
    t, c = Transport(), Career()
    return t, c, Worker(t, c, tmp_path / "bridge.sqlite", REQUESTERS)


def test_command_schema_covers_exact_allowlist():
    assert len(schema()["oneOf"]) == len(COMMANDS) == 15
    assert not {"execute", "accept", "authorize", "provision"} & COMMANDS.keys()


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(command="execute_match"),
        lambda r: r.update(path="C:/secret.sqlite"),
        lambda r: r.update(sequence=True),
        lambda r: r.update(sequence=1.0),
        lambda r: r.update(expected_checkpoint="../secret"),
        lambda r: r.update(career="../../evil"),
        lambda r: r.update(args={"fixture": "../../database.sqlite"}),
        lambda r: r.update(args={"code": "print('evil')"}),
    ],
)
def test_closed_schema_rejects_mutations(change):
    r = request()
    change(r)
    with pytest.raises(ValueError):
        parse(encode(r))


def test_duplicate_json_keys_and_nonfinite_rejected():
    with pytest.raises(ValueError):
        parse('{"protocol":"x","protocol":"y"}')
    with pytest.raises(ValueError):
        parse('{"sequence":NaN}')


def test_roundtrip_duplicate_id_and_ack(rig):
    t, c, w = rig
    r = request("narrate_next", fixture="league:1")
    a = t.add(r)
    w.poll()
    original = t.result(a)
    assert original["response"]["status"] == "completed" and c.position == 1
    b = t.add(r)
    w.poll()
    assert t.result(b) == original and c.position == 1
    assert all(i["state"] == "closed" for i in t.rows.values())
    assert w.verify_response(original)


@pytest.mark.parametrize(
    "stage",
    ["after_page_before_store", "after_response_before_post", "after_post_before_ack"],
)
def test_process_restart_resumes_original_page(rig, stage):
    t, c, w = rig
    n = t.add(request("narrate_next", fixture="league:1"))
    w.crash = stage
    with pytest.raises(RuntimeError):
        w.poll()
    restart = Worker(t, c, w.path, REQUESTERS)
    restart.poll()
    assert c.position == 1 and len(t.notes[n]) == 1
    assert t.result(n)["response"]["result"]["pages"][0]["events"][0]["sequence"] == 1


def test_until_halftime_and_continuation_new_conversation(rig):
    t, c, w = rig
    n = t.add(request("narrate_until_halftime", fixture="league:1"))
    w.poll()
    pages = t.result(n)["response"]["result"]["pages"]
    assert [e["sequence"] for p in pages for e in p["events"]] == [1, 2, 3]
    assert (
        pages[-1]["events"][-1]["kind"] == "HALF_TIME"
        and not pages[-1]["postmatch_available"]
    )
    restarted = Worker(t, c, w.path, REQUESTERS)
    n = t.add(request("narrate_next", 2, fixture="league:1"))
    restarted.poll()
    assert t.result(n)["response"]["result"]["pages"][0]["events"][0]["sequence"] == 4
    n = t.add(request("narrate_until_final", 3, fixture="league:1"))
    restarted.poll()
    assert t.result(n)["response"]["result"]["boundary_reached"] and c.position == 5


def test_network_post_uncertainty_is_reconciled(rig):
    t, c, w = rig
    n = t.add(request("narrate_next", fixture="league:1"))
    t.lost_post = True
    with pytest.raises(RuntimeError):
        w.poll()
    Worker(t, c, w.path, REQUESTERS).poll()
    assert len(t.notes[n]) == 1 and c.position == 1


def test_offline_then_reconnect(rig):
    t, c, w = rig
    n = t.add(request())
    t.offline = True
    with pytest.raises(RuntimeError):
        w.poll()
    assert not t.notes
    t.offline = False
    w.poll()
    assert t.result(n)["response"]["status"] == "completed"


def test_invalid_user_and_edited_issue_not_consumed(rig):
    t, c, w = rig
    t.add(request(), actor={"id": 2, "login": "Lbragaa"})
    t.add(request(), actor={"id": USER["id"], "login": "Imposter"})
    t.add(request(), edited="edited")
    w.poll()
    assert not t.notes
    with sqlite3.connect(w.path) as db:
        assert db.execute("SELECT next_sequence FROM meta").fetchone()[0] == 1


def test_future_result_and_wrong_head_refused_without_effect(rig):
    t, c, w = rig
    n = t.add(request("prematch_preview", fixture="league:999"))
    w.poll()
    assert t.result(n)["response"]["status"] == "refused" and c.position == 0
    r = request("narrate_next", 2, fixture="league:1")
    r["expected_checkpoint"] = "c" * 64
    n = t.add(r)
    w.poll()
    assert t.result(n)["response"]["status"] == "refused" and c.position == 0


def test_sequence_order_and_replay_collision(rig):
    t, c, w = rig
    future = request(sequence=2)
    a = t.add(future)
    b = t.add(request())
    w.poll()
    assert a not in t.notes and b in t.notes
    w.poll()
    assert a in t.notes
    altered = copy.deepcopy(future)
    altered["command"] = "next_event"
    n = t.add(altered)
    w.poll()
    assert n not in t.notes


def test_public_transport_and_tampered_ledger_fail_closed(rig):
    t, c, w = rig
    t.private = False
    t.add(request())
    with pytest.raises(RuntimeError):
        w.poll()
    assert not t.notes
    t.private = True
    with sqlite3.connect(w.path) as db:
        db.execute("UPDATE meta SET next_sequence=99")
    with pytest.raises(ValueError, match="integrity"):
        w.poll()


def test_scope_limits_repeat_and_manifest_preparation(rig):
    t, c, w = rig
    n = t.add(request("prepare_batch", until="2027-09-30 23:59"))
    w.poll()
    assert t.result(n)["response"]["result"]["execution_authorized"] is False
    original = t.result(n)
    r = request(
        "repeat_previous_delivery", 2, delivery_id=original["response"]["request_id"]
    )
    n = t.add(r)
    w.poll()
    assert t.result(n)["response"]["result"]["original_delivery"] == original
    assert c.position == 0


def test_transport_context_cannot_be_rebound(rig):
    t, c, w = rig
    t.repository_id += 1
    with pytest.raises(ValueError, match="different configured"):
        Worker(t, c, w.path, REQUESTERS).poll()
