import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from braga_era.config import database_path
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import load_baseline


@pytest.mark.parametrize("sql", [
    "UPDATE meta SET value='047' WHERE key='saved_state_version'",
    "DELETE FROM events", "CREATE TABLE corrupt (id INTEGER)",
    "PRAGMA query_only=OFF", "ATTACH DATABASE ':memory:' AS writable",
    "PRAGMA user_version=99", "VACUUM", "BEGIN IMMEDIATE",
])
def test_write_operations_denied(canonical_path, sql):
    before = file_sha256(canonical_path)
    with connect_read_only(canonical_path) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(sql)
    assert file_sha256(canonical_path) == before


def test_missing_path_never_created(tmp_path):
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError, match="bootstrap_handoff"):
        with connect_read_only(missing):
            pass
    assert not missing.exists()


def test_uri_escaping(canonical_path, tmp_path):
    path = tmp_path / "save #046 space.sqlite"
    shutil.copyfile(canonical_path, path)
    with connect_read_only(path) as connection:
        assert connection.execute("SELECT value FROM meta WHERE key='saved_state_version'").fetchone()[0] == "046"


def test_configuration_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAGA_ERA_DB", str(tmp_path / "environment.sqlite"))
    assert database_path().name == "environment.sqlite"
    assert database_path(tmp_path / "explicit.sqlite").name == "explicit.sqlite"
    monkeypatch.delenv("BRAGA_ERA_DB")
    assert database_path().name == "braga_save.sqlite"


@pytest.mark.parametrize("arguments,code,key", [
    (["inspect", "--json"], 0, "save_version"),
    (["audit", "--json"], 0, "ok"),
    (["audit", "--strict", "--json"], 1, "ok"),
])
def test_cli_outside_repository(canonical_path, tmp_path, arguments, code, key):
    env = {**os.environ, "BRAGA_ERA_DB": str(canonical_path), "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, "-m", "braga_era", *arguments], cwd=tmp_path,
                            env=env, capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == code, result.stderr
    assert key in json.loads(result.stdout)
    assert file_sha256(canonical_path) == load_baseline()["database_sha256"]


def test_cli_bad_path_json(tmp_path):
    path = tmp_path / "missing.sqlite"
    result = subprocess.run([sys.executable, "-m", "braga_era", "audit", "--db", str(path), "--json"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert json.loads(result.stdout)["ok"] is False
    assert not path.exists()


def test_cli_inspect_text_uses_real_summary(canonical_path):
    result = subprocess.run([sys.executable, "-m", "braga_era", "inspect", "--db", str(canonical_path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "Save 046" in result.stdout
    assert "Mirassol vs Vasco" in result.stdout
    assert "31,930,000" in result.stdout
