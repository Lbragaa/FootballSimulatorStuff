"""Human consent must be separate from an assistant's GitHub request."""

from copy import deepcopy
import sqlite3
from uuid import uuid4
import pytest

from braga_era.bridge.approval import HumanGate, PROFILE, otp
from braga_era.history import digest

KEY = b"task04c-public-test-signing-key-ONLY"
SECRET = b"12345678901234567890"  # RFC test vector, NOT production enrollment.
CONTEXT = {"profile": PROFILE, "career": "test-04c", "test_only": True,
           "repository_id": 1436541980, "human_id": 78325376, "human_login": "Lbragaa"}


@pytest.fixture
def gate(tmp_path):
    now = [1700000000]
    gate = HumanGate(tmp_path / "gate.sqlite", KEY, SECRET, CONTEXT, clock=lambda: now[0])
    gate.initialize()
    gate.now = now
    return gate


def statement(action="authorize_batch"):
    return {"action": action, "career": "test-04c", "test_only": True,
            "repository_id": 1436541980, "target_sha256": "a" * 64}


def challenge(gate, action="authorize_batch", issue=6):
    cid = str(uuid4())
    return gate.challenge(cid, issue, statement(action))


def comment(gate, challenge, **changes):
    value = {"id": 123, "user": {"id": 78325376, "login": "Lbragaa"},
             "body": challenge["confirmation_format"].replace("<authenticator-code>", otp(SECRET, gate.now[0] // 30)),
             "created_at": "2026-10-28T05:00:00Z", "updated_at": "2026-10-28T05:00:00Z"}
    value.update(changes)
    return value


def test_rfc6238_vectors():
    assert otp(SECRET, 59 // 30) == "287082"
    assert otp(SECRET, 1111111109 // 30) == "081804"
    assert otp(SECRET, 20000000000 // 30) == "353130"


def test_confirm_once_replay_and_new_gate_object(gate):
    ch = challenge(gate)
    effects = []
    def perform(s, proof):
        effects.append(s)
        assert proof["document"]["statement_sha256"] == digest(s)
        return {"done": True}
    assert gate.confirm(ch["challenge_id"], 6, comment(gate, ch), perform) == {"done": True}
    assert gate.confirm(ch["challenge_id"], 6, {}, perform) == {"done": True}
    restarted = HumanGate(gate.path, KEY, SECRET, CONTEXT, clock=gate.clock)
    assert restarted.resume(ch["challenge_id"], perform) == {"done": True}
    assert len(effects) == 1


@pytest.mark.parametrize("change", [
    {"user": {"id": 1, "login": "Lbragaa"}},
    {"user": {"id": 78325376, "login": "another"}},
    {"performed_via_github_app": {"id": 1}},
    {"updated_at": "2026-10-28T05:00:01Z"},
    {"body": "I approve everything"},
    {"body": "BRAGA_CONFIRM_V1 code only"},
])
def test_untrusted_or_general_chat_is_not_consent(gate, change):
    ch = challenge(gate)
    with pytest.raises(ValueError):
        gate.confirm(ch["challenge_id"], 6, comment(gate, ch, **change), lambda *_: pytest.fail("must not execute"))


def test_wrong_hash_issue_expiration_and_changed_request(gate):
    ch = challenge(gate)
    changed = comment(gate, ch)
    changed["body"] = changed["body"].replace(ch["binding_sha256"], "b" * 64)
    with pytest.raises(ValueError):
        gate.confirm(ch["challenge_id"], 6, changed, lambda *_: None)
    with pytest.raises(ValueError):
        gate.confirm(ch["challenge_id"], 7, comment(gate, ch), lambda *_: None)
    with pytest.raises(ValueError):
        gate.challenge(ch["challenge_id"], 6, statement("execute_batch"))
    gate.now[0] += 601
    with pytest.raises(ValueError):
        gate.confirm(ch["challenge_id"], 6, comment(gate, ch), lambda *_: None)


def test_authenticator_counter_cannot_authorize_second_action(gate):
    ch = challenge(gate)
    gate.confirm(ch["challenge_id"], 6, comment(gate, ch), lambda *_: {})
    second = challenge(gate, "execute_batch", 7)
    with pytest.raises(ValueError, match="replayed"):
        gate.confirm(second["challenge_id"], 7, comment(gate, second, id=124), lambda *_: pytest.fail())
    gate.now[0] += 30
    assert gate.confirm(second["challenge_id"], 7, comment(gate, second, id=124), lambda *_: {"ok": True})["ok"]


def test_crash_proof_precedes_mutation_and_resumes_same_action(gate):
    ch = challenge(gate)
    calls = []
    def interrupted(s, proof):
        calls.append(proof)
        raise RuntimeError("crash after external transaction")
    with pytest.raises(RuntimeError):
        gate.confirm(ch["challenge_id"], 6, comment(gate, ch), interrupted)
    gate.now[0] += 3600  # committed consent survives expiry for exact resumption.
    def resume(s, proof):
        assert proof == calls[0]
        return {"original_receipt": True}
    assert gate.resume(ch["challenge_id"], resume)["original_receipt"]


def test_missing_tampered_rebound_and_reset_gate_fail_closed(gate):
    with pytest.raises(ValueError):
        gate.initialize()
    altered = deepcopy(CONTEXT)
    altered["test_only"] = False
    with pytest.raises(ValueError):
        HumanGate(gate.path, KEY, SECRET, altered).challenge(str(uuid4()), 6, statement())
    with pytest.raises(ValueError):
        HumanGate(gate.path, KEY, b"different-enrollment-secret-1234", CONTEXT).challenge(str(uuid4()), 6, statement())
    with sqlite3.connect(gate.path) as c:
        c.execute("UPDATE configuration SET last_counter=-20")
    with pytest.raises(ValueError, match="integrity"):
        challenge(gate)


def test_guessing_limit_and_single_outstanding_action(gate):
    ch = challenge(gate)
    with pytest.raises(ValueError, match="single active"):
        challenge(gate, "execute_batch", 7)
    for index in range(11):
        code = (int(otp(SECRET, gate.now[0] // 30)) + 123) % 1000000
        body = ch["confirmation_format"].replace("<authenticator-code>", f"{code:06}")
        with pytest.raises(ValueError, match="limit" if index == 10 else "authenticator"):
            gate.confirm(ch["challenge_id"], 6, comment(gate, ch, body=body, id=500 + index), lambda *_: pytest.fail())


def test_expired_challenge_can_be_replaced_but_committed_one_must_resume(gate):
    ch = challenge(gate)
    gate.now[0] += 601
    replacement = challenge(gate, "execute_batch", 7)
    with pytest.raises(RuntimeError):
        gate.confirm(replacement["challenge_id"], 7, comment(gate, replacement),
                     lambda *_: (_ for _ in ()).throw(RuntimeError("interrupted")))
    gate.now[0] += 601
    with pytest.raises(ValueError, match="single active"):
        challenge(gate, "accept_candidate", 8)
