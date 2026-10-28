import json
from pathlib import Path
import pytest
from braga_era.bridge.__main__ import config
from braga_era.bridge.github import GitHub, TransportError, NoRedirect
from braga_era.bridge.worker import Worker
from test_bridge import Career, Transport, REQUESTERS, request


def sample(tmp_path):
    return {
        "repository": "Lbragaa/BragaEraCommandBridge",
        "repository_id": 1436541980,
        "worker_id": 78325376,
        "requesters": json.loads(json.dumps(REQUESTERS)),
        "registry": str(tmp_path / "authority.sqlite"),
        "key_file": str(tmp_path / "key"),
        "ledger": str(tmp_path / "ledger.sqlite"),
        "career": "test-career",
        "test_only": True,
        "credential_target": "BragaEraBridge/test/github",
        "poll_seconds": 15,
        "production_binding_approved": False,
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(test_only=False),
        lambda c: c.update(test_only="false"),
        lambda c: c.update(poll_seconds=True),
        lambda c: c.update(key_file="../key"),
        lambda c: c.update(worker_id=True),
        lambda c: c.update(shell="evil"),
        lambda c: c["requesters"]["78325376"].update(scopes=["execute"]),
    ],
)
def test_bad_configuration_fails_closed(tmp_path, change):
    v = sample(tmp_path)
    change(v)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(v))
    with pytest.raises(ValueError):
        config(p)


def test_redirects_and_repository_injection_refused():
    with pytest.raises(TransportError):
        NoRedirect().redirect_request(
            None, None, 302, "", {}, "https://elsewhere.invalid"
        )
    with pytest.raises(ValueError):
        GitHub("owner/repo/../../x", 1, 1, "unused")


def test_wrong_worker_and_public_repo_refused():
    g = GitHub("owner/repo", 1, 2, "unused")
    g.call = lambda suffix, **kwargs: (
        {"id": 3}
        if kwargs.get("account")
        else {"id": 1, "private": True, "archived": False}
    )
    with pytest.raises(TransportError):
        g.privacy()
    g.call = lambda suffix, **kwargs: {"id": 1, "private": False}
    with pytest.raises(TransportError):
        g.privacy()


def test_scope_revoked_before_delivery_does_not_publish(tmp_path):
    t, c = Transport(), Career()
    n = t.add(request())
    w = Worker(
        t, c, tmp_path / "ledger.sqlite", REQUESTERS, crash="after_response_before_post"
    )
    with pytest.raises(RuntimeError):
        w.poll()
    Worker(t, c, w.path, {}).poll()
    assert not t.notes


def test_edited_pinned_body_does_not_receive_another_response(tmp_path):
    t, c = Transport(), Career()
    r = request()
    n = t.add(r)
    w = Worker(
        t, c, tmp_path / "ledger.sqlite", REQUESTERS, crash="after_response_before_post"
    )
    with pytest.raises(RuntimeError):
        w.poll()
    t.rows[n]["body"] = t.rows[n]["body"].replace("inspect_career", "current_table")
    Worker(t, c, w.path, REQUESTERS).poll()
    assert not t.notes


def test_credential_manager_requires_fine_grained_pat(monkeypatch):
    from braga_era.bridge import credentials

    monkeypatch.setattr(
        credentials,
        "api",
        lambda: (_ for _ in ()).throw(AssertionError("No storage allowed")),
    )
    with pytest.raises(ValueError):
        credentials.write("test", "gho_NOT_A_FINE_GRAINED_TOKEN")


def test_startup_only_explicit_local_action(tmp_path):
    from braga_era.bridge.__main__ import main

    p = tmp_path / "config.json"
    p.write_text(json.dumps(sample(tmp_path)))
    assert main(["--config", str(p), "startup-enable"]) == 2


def test_generated_schema_equals_committed_reference():
    from braga_era.bridge.protocol import schema

    assert json.loads(Path("docs/bridge_request.schema.json").read_text()) == schema()
    from braga_era.bridge.protocol import response_schema

    assert (
        json.loads(Path("docs/bridge_response.schema.json").read_text())
        == response_schema()
    )


def test_missing_persistent_ledger_is_not_silently_recreated(tmp_path, monkeypatch):
    from braga_era.bridge.__main__ import main
    from braga_era.bridge import credentials

    v = sample(tmp_path)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(v))
    monkeypatch.setattr(
        credentials,
        "read",
        lambda _: (_ for _ in ()).throw(AssertionError("No credential read allowed")),
    )
    assert main(["--config", str(p), "run"]) == 2
    assert not Path(v["ledger"]).exists()
