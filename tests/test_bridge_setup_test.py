import json
from pathlib import Path
import pytest
from braga_era.bridge import setup_test
from braga_era.bridge.__main__ import config
from braga_era.db import file_sha256
from braga_era import lineage


def test_fresh_phone_test_setup_does_not_execute_or_bind_production(tmp_path, accepted_path):
    before = file_sha256(accepted_path)
    p = setup_test.create(accepted_path, tmp_path / "phone")
    value = config(p)
    assert value["test_only"] and not value["production_binding_approved"]
    assert not value["control"]["enabled"]
    key = Path(value["key_file"]).read_bytes()
    with lineage.access(value["registry"], key) as (c, t):
        assert t["head"] == lineage.ROOT and t["test_only"]
        assert c.execute("SELECT count(*) FROM batches").fetchone()[0] == 0
    with pytest.raises(ValueError):
        setup_test.create(accepted_path, tmp_path / "phone")
    assert file_sha256(accepted_path) == before


def test_enrollment_cannot_be_production_or_noninteractive(tmp_path, accepted_path, monkeypatch, capsys):
    p = setup_test.create(accepted_path, tmp_path / "phone")
    with pytest.raises(ValueError, match="Explicit"):
        setup_test.enroll(p)
    monkeypatch.setattr(setup_test.sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="interactive"):
        setup_test.enroll(p, True)
    assert "Setup key:" not in capsys.readouterr().out
    value = config(p)
    value["test_only"] = False
    value["production_binding_approved"] = True
    p.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="TEST-ONLY"):
        setup_test.enroll(p, True)


def test_enrollment_never_recreates_a_lost_inbox(tmp_path, accepted_path):
    p = setup_test.create(accepted_path, tmp_path / "phone")
    value = config(p)
    Path(value["ledger"]).unlink()
    with pytest.raises(ValueError, match="Missing established"):
        setup_test.enroll(p, True)
    assert not Path(value["ledger"]).exists()
