from contextlib import closing
import copy
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile

import pytest

from braga_era.calendar import CalendarError, CalendarPolicy, Event, inventory, propose, solve, validate_plan
from braga_era.checkpoints import (REQUIRED_APPROVALS, create_candidate, export_checkpoint, export_parent,
    manifest_for, promote_candidate, read_json, restore_checkpoint, verify_checkpoint, write_json)
from braga_era.config import database_path
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import load_baseline, table_fingerprint
from braga_era.migrations import apply
from braga_era.payroll import book_payroll, financial_statement, obligations
from braga_era.profiles import audit_046c, load_046c_plan, verify_database


@pytest.fixture(scope="session")
def candidate(canonical_path, tmp_path_factory):
    path = tmp_path_factory.mktemp("checkpoint") / "046C"
    create_candidate(canonical_path, path)
    return path


def test_candidate_state_history_and_finance(candidate, canonical_path):
    report = verify_checkpoint(candidate)
    assert report["ok"]
    assert report["metadata"]["status"] == "candidate"
    assert report["metadata"]["canonical_promoted"] is False
    assert report["validation"]["failures"] == 0
    assert report["metadata"]["operation_count"] == 119
    assert len(read_json(candidate / "changes.json")) == 238
    with connect_read_only(candidate / "database.sqlite") as c:
        info = dict(c.execute("SELECT key,value FROM meta"))
        assert (info["saved_state_version"], info["current_date"]) == ("046C", "2027-09-26 23:30")
        f = financial_statement(c)
        assert f["restricted_cash_cents"] == 3_055_000_000
        assert f["accrued_unpaid_cents"] == 155_900_001
        assert f["cash_less_recorded_incremental_liability_cents"] == 2_899_099_999
        assert f["annual_incremental_commitments_cents"] == 2_166_000_000
        sept = next(p for p in f["periods"] if p["period"] == "2027-09")
        assert (sept["amount_due_cents"], sept["cash_cents"], sept["ledger_id"]) == (179_966_667, 0, None)
        board = {r["competition"]: dict(r) for r in c.execute("SELECT * FROM board_objectives")}
        assert [board[k]["achieved"] for k in ("Campeonato Carioca", "Copa do Brasil", "Copa Sul-Americana")] == ["achieved", "achieved", "failed"]
        assert all(board[k]["achieved"] == "pending" for k in ("Brasileirão", "Youth", "Finance"))
        assert "R$68m" in board["Finance"]["objective"]
        assert table_fingerprint(c, "fixtures") == load_baseline()["tables"]["fixtures"]
        assert table_fingerprint(c, "players") == load_baseline()["tables"]["players"]
    assert file_sha256(canonical_path) == load_baseline()["database_sha256"]
    assert database_path() == canonical_path


def test_reconciliation_is_byte_and_report_deterministic(candidate, canonical_path, tmp_path):
    second = tmp_path / "same"
    create_candidate(canonical_path, second)
    assert manifest_for(second) == manifest_for(candidate)
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    export_checkpoint(candidate, a)
    export_checkpoint(second, b)
    assert file_sha256(a) == file_sha256(b)


def test_calendar_solver_reproduces_checked_in_plan(canonical):
    assert propose(canonical) == load_046c_plan()
    feasibility = validate_plan(canonical, load_046c_plan())
    assert feasibility["feasible"]
    assert feasibility["minimum_new_turnaround_hours"] == 72
    assert len(feasibility["inherited_league_rest_exceptions"]) == 12
    assert feasibility["league_fixtures_moved"] == 0


def test_extra_travel_model_reports_unsatisfiable(canonical):
    with pytest.raises(CalendarError, match="No schedule"):
        propose(canonical, CalendarPolicy(international_buffer_hours=6))


def test_calendar_detects_collision_and_bracket_edit(canonical):
    plan = copy.deepcopy(load_046c_plan())
    event = next(e for e in plan["events"] if e["event_id"] == "CDB:QF-01:L1")
    event["kickoff"] = "2027-10-02 18:00"  # Fluminense already plays the league.
    assert not validate_plan(canonical, plan)["feasible"]
    event["clubs"] = ["Vasco"]
    assert any("Bracket definition" in p for p in validate_plan(canonical, plan)["problems"])


def test_unsatisfiable_schedule_and_cycles_are_explicit():
    now = datetime(2027, 9, 26, 23, 30)
    events = [Event("a", "X", "QF", 1, ("Vasco",)), Event("b", "X", "QF", 2, ("Vasco",), ("a",))]
    with pytest.raises(CalendarError):
        solve(events, [], now, CalendarPolicy(deadline="2027-09-28 21:00"))
    cyclic = [Event("a", "X", "QF", 1, ("Vasco",), ("b",)), events[1]]
    with pytest.raises(CalendarError, match="Cyclic"):
        solve(cyclic, [], now, CalendarPolicy())


@pytest.mark.parametrize("point", ["calendar", "payroll", "operations"])
def test_partial_migration_rolls_back(canonical_path, tmp_path, point):
    path = tmp_path / "scratch.sqlite"
    shutil.copyfile(canonical_path, path)
    with closing(sqlite3.connect(path)) as c:
        c.row_factory = sqlite3.Row
        with pytest.raises(RuntimeError, match="Injected"):
            apply(c, load_046c_plan(), load_baseline()["database_sha256"], fail_after=point)
        assert c.execute("SELECT count(*) FROM sqlite_master WHERE name='checkpoint_info'").fetchone()[0] == 0
        assert c.execute("SELECT value FROM meta WHERE key='saved_state_version'").fetchone()[0] == "046"
        assert c.execute("SELECT count(*) FROM finance_ledger").fetchone()[0] == 21
    assert file_sha256(path) == file_sha256(canonical_path)


def test_failed_candidate_is_not_published(canonical_path, tmp_path):
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError):
        create_candidate(canonical_path, output, fail_after="payroll")
    assert not output.exists()
    assert not list(tmp_path.glob(".failed.*"))


def test_duplicate_payroll_and_early_payment(candidate, tmp_path):
    path = tmp_path / "scratch.sqlite"
    shutil.copyfile(candidate / "database.sqlite", path)
    with closing(sqlite3.connect(path)) as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN IMMEDIATE")
        before = c.execute("SELECT count(*) FROM finance_ledger").fetchone()[0]
        ledger_id, inserted = book_payroll(c, "2027-08", 138_000_000, "2027-09-26")
        assert (ledger_id, inserted) == (22, False)
        assert c.execute("SELECT count(*) FROM finance_ledger").fetchone()[0] == before
        with pytest.raises(ValueError, match="Conflicting"):
            book_payroll(c, "2027-08", 138_000_001, "2027-09-26")
        with pytest.raises(ValueError, match="month-end"):
            book_payroll(c, "2027-09", 179_966_667, "2027-09-26")
        # September posting can succeed later despite August's arrears being
        # dated in September; stable period linkage avoids false duplicates.
        _, inserted = book_payroll(c, "2027-09", 179_966_667, "2027-09-30")
        assert inserted
        assert book_payroll(c, "2027-09", 179_966_667, "2027-09-30")[1] is False
        assert financial_statement(c)["accrued_unpaid_cents"] == 0
        c.rollback()  # No future state from this test is promoted.


def test_payroll_guard_unregistered_duplicate_and_reserve(candidate, tmp_path):
    path = tmp_path / "scratch.sqlite"
    shutil.copyfile(candidate / "database.sqlite", path)
    with closing(sqlite3.connect(path)) as c:
        c.row_factory = sqlite3.Row
        c.execute("BEGIN")
        c.execute("INSERT INTO finance_ledger(dated,category,account,amount_brl,restricted_for,description) VALUES('2027-09-30','incremental wage payroll','2027 football restricted account',-1,'test','2027-09 duplicate')")
        with pytest.raises(ValueError, match="duplicate"):
            book_payroll(c, "2027-09", 179_966_667, "2027-09-30")
        c.rollback()
        c.execute("BEGIN")
        c.execute("INSERT INTO finance_ledger(dated,category,account,amount_brl,restricted_for,description) VALUES('2027-09-26','incremental wage payroll','2027 football restricted account',-1380000,'test','2027-08 duplicate')")
        with pytest.raises(ValueError, match="duplicate"):
            book_payroll(c, "2027-08", 138_000_000, "2027-09-26")
        c.rollback()
        c.execute("BEGIN")
        c.execute("UPDATE finance_budget SET amount_brl=30550000 WHERE category='Emergency reserve'")
        with pytest.raises(ValueError, match="reserve"):
            book_payroll(c, "2027-09", 179_966_667, "2027-09-30")
        c.rollback()


def test_wrong_parent_and_incompatible_version(canonical_path, tmp_path):
    parent = tmp_path / "wrong.sqlite"
    shutil.copyfile(canonical_path, parent)
    with closing(sqlite3.connect(parent)) as c:
        c.execute("UPDATE meta SET value='047' WHERE key='saved_state_version'")
        c.commit()
    with pytest.raises(ValueError, match="checksum"):
        create_candidate(parent, tmp_path / "candidate")
    with pytest.raises(ValueError, match="registered"):
        create_candidate(canonical_path, tmp_path / "candidate", version="047")


@pytest.mark.parametrize("sql", [
    "UPDATE fixtures SET home_goals=9 WHERE id=322",
    "UPDATE events SET minute=83 WHERE fixture_id=322 AND player_id=32",
    "UPDATE players SET name='erased' WHERE id=196",
    "UPDATE finance_ledger SET amount_brl=0 WHERE id=22",
    "INSERT INTO finance_ledger SELECT 23,dated,category,account,amount_brl,restricted_for,description,fictional FROM finance_ledger WHERE id=22",
    "UPDATE calendar_events SET kickoff='2027-10-02 18:00' WHERE event_id='CDB:QF-01:L1'",
    "UPDATE board_objectives SET achieved='achieved' WHERE competition='Finance'",
    "UPDATE admin_operations SET reason='unlogged action' WHERE sequence=1",
    "CREATE TABLE unauthorized(id INTEGER)",
])
def test_046c_rejects_unauthorized_changes(candidate, canonical_path, tmp_path, sql):
    path = tmp_path / "corrupt.sqlite"
    shutil.copyfile(candidate / "database.sqlite", path)
    with closing(sqlite3.connect(path)) as c:
        c.execute(sql)
        c.commit()
    with connect_read_only(path) as c:
        report = audit_046c(c, path, canonical_path)
    assert not report.ok
    assert any(f.status == "FAIL" and f.code.startswith("046c.") for f in report.findings)


def test_portable_parent_and_candidate_restore(candidate, canonical_path, tmp_path):
    candidate_zip = tmp_path / "046C.zip"
    parent_zip = tmp_path / "046.zip"
    export_checkpoint(candidate, candidate_zip)
    export_parent(canonical_path, parent_zip)
    restored = tmp_path / "restore candidate #046C"
    parent = tmp_path / "restore parent #046"
    assert restore_checkpoint(candidate_zip, restored)["ok"]
    assert restore_checkpoint(parent_zip, parent)["ok"]
    assert file_sha256(restored / "database.sqlite") == file_sha256(candidate / "database.sqlite")
    assert file_sha256(parent / "database.sqlite") == load_baseline()["database_sha256"]
    assert verify_database(restored / "database.sqlite", "046C", parent / "database.sqlite").ok


def test_overwrites_refused(candidate, canonical_path, tmp_path):
    with pytest.raises(FileExistsError):
        create_candidate(canonical_path, candidate)
    with pytest.raises(FileExistsError):
        create_candidate(canonical_path, canonical_path)
    with pytest.raises(FileExistsError):
        create_candidate(canonical_path, canonical_path.parent / "never-write-here")
    archive = tmp_path / "save.zip"
    export_checkpoint(candidate, archive)
    with pytest.raises(FileExistsError):
        export_checkpoint(candidate, archive)
    with pytest.raises(FileExistsError):
        restore_checkpoint(archive, candidate)


def test_manifest_tampering_and_resealed_history_rejected(candidate, tmp_path):
    changed = tmp_path / "changed"
    shutil.copytree(candidate, changed)
    (changed / "report.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        verify_checkpoint(changed)
    # Recomputing a manifest cannot authorize rewriting history or reports.
    write_json(changed / "manifest.json", manifest_for(changed))
    with pytest.raises(ValueError, match="Narrative"):
        verify_checkpoint(changed)
    with closing(sqlite3.connect(changed / "database.sqlite")) as c:
        c.execute("UPDATE fixtures SET away_goals=5 WHERE id=322")
        c.commit()
    write_json(changed / "manifest.json", manifest_for(changed))
    with pytest.raises(ValueError, match="validation profile"):
        verify_checkpoint(changed)


def test_hidden_file_not_covered_by_manifest_is_rejected(candidate, tmp_path):
    changed = tmp_path / "changed"
    shutil.copytree(candidate, changed)
    (changed / "nested").mkdir()
    (changed / "nested/manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        verify_checkpoint(changed)


@pytest.mark.parametrize("name", ["../escape", "/escape", "C:/escape", "folder\\escape"])
def test_archive_traversal_rejected(tmp_path, name):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as z:
        info = zipfile.ZipInfo()
        info.filename = name
        z.writestr(info, b"bad")
    with pytest.raises(ValueError, match="Unsafe"):
        restore_checkpoint(archive, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_explicit_promotion_gate_only_touches_scratch_pointer(candidate, tmp_path):
    metadata = read_json(candidate / "checkpoint.json")
    registry = tmp_path / "canonical.json"
    args = {"expected_parent_sha256": metadata["parent_sha256"],
            "approved_candidate_sha256": metadata["database_sha256"], "approvals": []}
    with pytest.raises(ValueError, match="approvals"):
        promote_candidate(candidate, registry, **args)
    assert not registry.exists()
    args["approvals"] = REQUIRED_APPROVALS
    promoted = promote_candidate(candidate, registry, **args)
    assert promoted["save_version"] == "046C"
    with pytest.raises(ValueError, match="parent conflict"):
        promote_candidate(candidate, registry, **args)
    assert read_json(candidate / "checkpoint.json")["status"] == "candidate"


def test_046c_cli_inspection_and_profile(candidate, canonical_path):
    result = subprocess.run([sys.executable, "-m", "braga_era", "inspect", "--db", str(candidate / "database.sqlite"), "--json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["checkpoint"]["status"] == "candidate"
    assert state["finance"]["payroll_months"][-1] == "2027-08"
    result = subprocess.run([sys.executable, "-m", "braga_era", "audit", "--profile", "046C", "--parent", str(canonical_path), "--db", str(candidate / "database.sqlite"), "--json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"]
