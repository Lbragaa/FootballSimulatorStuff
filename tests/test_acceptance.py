import json
from pathlib import Path

import pytest

from braga_era.acceptance import accepted_context, catalog
from braga_era.cli import main
from braga_era.config import database_path
from tools.bootstrap_accepted import install


def registry(accepted_path, tmp_path, monkeypatch):
    record = {
        **catalog(),
        "registry_format": 1,
        "checkpoint_directory": str(accepted_path.parent),
    }
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setenv("BRAGA_ERA_REGISTRY", str(path))
    return path


def test_registered_default_and_explicit_override(accepted_path, tmp_path, monkeypatch):
    registry(accepted_path, tmp_path, monkeypatch)
    assert database_path() == accepted_path.resolve()
    assert database_path(tmp_path / "explicit.sqlite").name == "explicit.sqlite"
    monkeypatch.setenv("BRAGA_ERA_DB", str(tmp_path / "env.sqlite"))
    assert database_path().name == "env.sqlite"


def test_registry_hash_mismatch_fails_closed(accepted_path, tmp_path, monkeypatch):
    path = registry(accepted_path, tmp_path, monkeypatch)
    record = json.loads(path.read_text())
    record["database_sha256"] = "0" * 64
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="differs"):
        database_path()


def test_acceptance_is_external_and_does_not_grant_match_authority(
    accepted_path, canonical_path
):
    context = accepted_context(accepted_path)
    assert context["status"] == "accepted_administrative_checkpoint"
    assert context["official_match_execution_authorized"] is False
    assert accepted_context(canonical_path) is None


def test_inspect_and_auto_audit_use_exact_accepted_checkpoint(
    accepted_path, tmp_path, monkeypatch, capsys
):
    registry(accepted_path, tmp_path, monkeypatch)
    assert main(["inspect", "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["acceptance"]["status"] == "accepted_administrative_checkpoint"
    assert (
        state["checkpoint"]["status"] == "candidate"
    )  # approved immutable bytes preserved
    assert main(["audit", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert main(["audit", "--profile", "046", "--json"]) == 1
    assert not json.loads(capsys.readouterr().out)["ok"]


def test_bootstrap_rejects_unapproved_bytes(tmp_path):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"not the approved artifact")
    with pytest.raises(ValueError, match="SHA256"):
        install(archive, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_missing_accepted_bytes_fail_closed(accepted_path, tmp_path, monkeypatch):
    path = registry(accepted_path, tmp_path, monkeypatch)
    record = json.loads(path.read_text())
    record["checkpoint_directory"] = "missing"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="missing"):
        database_path()
