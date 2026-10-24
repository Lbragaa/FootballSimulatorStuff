import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

from braga_era.audit import audit
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import completed_fixtures, digest, load_baseline
from braga_era.state import summary


def test_save046_baseline(canonical, canonical_path):
    before = file_sha256(canonical_path)
    report = audit(canonical, canonical_path)
    assert report.ok, report.to_dict()
    assert report.to_dict()["warnings"] == 10
    assert file_sha256(canonical_path) == before == load_baseline()["database_sha256"]


def test_canonical_state(canonical):
    state = summary(canonical)
    assert (state["save_version"], state["current_date"], state["board_confidence"], state["manager_matches"]) == (
        "046", "2027-09-26 23:30", 61, 45)
    assert state["league"] == {"clubs": 20, "final": 250, "scheduled": 130}
    assert tuple(state["vasco"][k] for k in ("position", "points", "played", "wins", "draws", "losses", "gf", "ga")) == (
        9, 38, 25, 11, 5, 9, 36, 37)
    assert (state["next_fixture"]["home"], state["next_fixture"]["away"], state["next_fixture"]["status"]) == (
        "Mirassol", "Vasco", "scheduled")
    assert state["next_fixture"]["home_goals"] is None
    assert state["finance"]["restricted_cash_brl"] == 31_930_000
    assert state["overdue_ties"] == {"Libertadores R16": 8, "Sudamericana playoffs": 8, "Copa do Brasil QF": 4}
    assert all(state["competitions"][cup]["vasco_status"] == "eliminated"
               for cup in ("Carioca", "Sudamericana", "Copa do Brasil"))


def test_historical_fixture_snapshot(canonical):
    baseline = load_baseline()
    fixtures = completed_fixtures(canonical)
    assert len(fixtures) == 331
    assert fixtures == baseline["completed_fixtures"]
    assert digest(fixtures) == baseline["completed_fixtures_sha256"]
    game = next(f for f in fixtures if f["id"] == 322)
    assert (game["home_goals"], game["away_goals"], game["round"], game["status"]) == (3, 2, "R25", "final")


def test_rojas_enters_before_winner(canonical):
    events = canonical.execute("SELECT event_type FROM events WHERE fixture_id=322 AND player_id=32 ORDER BY minute,id")
    assert [r[0] for r in events] == ["SUBSTITUTION", "GOAL"]


@pytest.mark.parametrize("sql,expected_failure", [
    ("UPDATE fixtures SET home_goals=4 WHERE id=322", "vasco.palmeiras"),
    ("UPDATE fixtures SET report='rewritten history' WHERE id=1", "history.completed_fixtures"),
    ("DELETE FROM fixtures WHERE id=322", "league.inventory"),
    ("UPDATE fixtures SET status='final',home_goals=1,away_goals=0 WHERE id=332", "league.inventory"),
    ("UPDATE clubs SET points=99 WHERE name='Vasco'", "league.standings"),
    ("UPDATE events SET player_id=29 WHERE fixture_id=322 AND player_id=32 AND event_type='GOAL'", "r25.rojas_order"),
    ("UPDATE players SET name='merged' WHERE id=196", "players.identities"),
    ("UPDATE finance_ledger SET amount_brl=0 WHERE id=16", "finance.cash"),
    ("UPDATE finance_budget SET amount_brl=99000000 WHERE category='Transfer fees'", "finance.authority"),
    ("UPDATE meta SET value='047' WHERE key='saved_state_version'", "save046.meta"),
    ("UPDATE libertadores_2027_fixtures SET home_goals=99 WHERE id=(SELECT min(id) FROM libertadores_2027_fixtures)", "history.all_tables"),
    ("UPDATE cdb_2027_legs SET hg=99 WHERE tie_code='R16-01'", "history.all_tables"),
    ("UPDATE transfers SET fee_brl=0 WHERE id=1", "history.all_tables"),
])
def test_audit_detects_tampering_only_on_temporary_copies(canonical_path, tmp_path, sql, expected_failure):
    path = tmp_path / "test.sqlite"
    shutil.copyfile(canonical_path, path)
    with sqlite3.connect(path) as writable:
        writable.execute(sql)
    with connect_read_only(path) as connection:
        report = audit(connection, path)
    failures = {f.code for f in report.findings if f.status == "FAIL"}
    assert not report.ok
    assert expected_failure in failures
    assert "history.database_sha256" in failures
    assert file_sha256(canonical_path) == load_baseline()["database_sha256"]


def test_missing_schema_is_reported(tmp_path):
    path = tmp_path / "empty.sqlite"
    sqlite3.connect(path).close()
    with connect_read_only(path) as connection:
        report = audit(connection, path)
    assert not report.ok
    assert any(f.code == "history.tables" and f.status == "FAIL" for f in report.findings)


def test_original_verifier(canonical_path):
    root = canonical_path.parents[1]
    result = subprocess.run([sys.executable, str(root / "tools/verify_handoff.py")],
                            capture_output=True, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"}, check=False)
    assert result.returncode == 0, result.stderr
    assert "canonical Save046 verified" in result.stdout
