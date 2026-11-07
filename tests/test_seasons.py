"""Disconnected lifecycle fixtures only; no production configuration or authority."""
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import sqlite3
from uuid import uuid4

import pytest

from braga_era.db import connect_read_only, file_sha256
from braga_era.seasons import (AcceptedSource, closure_report, create_rehearsal,
                              double_round_robin, inspect_rehearsal, transition)
from test_bridge_career import actual


@pytest.fixture
def policy():
    return {"version": "season-lifecycle-proposal-1", "season": 2027, "next_season": 2028,
            "competitions": [{"id": "LEAGUE", "minimum_completed": 12,
                              "cross_year": False, "requires_champion": True}]}


@pytest.fixture
def completed(tmp_path):
    path = tmp_path / "TEST-ONLY-completed.sqlite"
    with sqlite3.connect(path) as c:
        c.executescript('''
CREATE TABLE clubs(id INTEGER PRIMARY KEY,name TEXT);
CREATE TABLE fixtures(id INTEGER PRIMARY KEY,competition TEXT,datetime_local TEXT,"round" TEXT,home_id INTEGER,away_id INTEGER,home_goals INTEGER,away_goals INTEGER,status TEXT);
CREATE TABLE competition_history(season INTEGER,competition TEXT,winner TEXT);
CREATE TABLE world_obligations(key TEXT PRIMARY KEY,kickoff TEXT,status TEXT);
CREATE TABLE identity_evidence(id INTEGER PRIMARY KEY,detail TEXT);
INSERT INTO identity_evidence VALUES(196,'archived Savarino'),(354,'active Savarino');
INSERT INTO competition_history VALUES(2027,'Brasileirão 2027','TEST Club 1');
''')
        for i in range(1, 5):
            c.execute("INSERT INTO clubs VALUES(?,?)", (i, "TEST Club " + str(i)))
        for i, f in enumerate(double_round_robin(["1", "2", "3", "4"], season=2027), 1):
            c.execute("INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)",
                      (i, "Brasileirão 2027", "2028-01-03 16:00", "R"+str(f["round"]), int(f["home"]), int(f["away"]), 1, 0, "final"))
    return path


def rehearsal(completed, tmp_path, policy):
    # Toy accepted-source adapter is deliberately local to these tests. Production
    # uses AcceptedSource.career (registered signatures), not arbitrary files.
    return create_rehearsal(AcceptedSource(completed, "TEST-parent", file_sha256(completed)), tmp_path / "rehearsal", policy)


def test_root_authentication_and_incomplete_real_season(accepted_path, tmp_path):
    policy = {"version": "season-lifecycle-proposal-1", "season": 2027, "next_season": 2028,
              "competitions": [{"id": k, "minimum_completed": n, "cross_year": False, "requires_champion": True}
                               for k,n in (("LEAGUE",380),("CDB",48),("LIB",112),("SULA",112),("CARIOCA",5))]}
    before = file_sha256(accepted_path)
    report = create_rehearsal(AcceptedSource.root(accepted_path), tmp_path / "root-rehearsal", policy)
    assert not report["closure"]["ready_to_finalize"]
    with pytest.raises(ValueError, match="cannot close"):
        transition(tmp_path / "root-rehearsal", "season_finalizing", request_id=str(uuid4()))
    assert file_sha256(accepted_path) == before
    fake = tmp_path / "fake.sqlite"
    fake.write_bytes(b"unaccepted")
    with pytest.raises(ValueError, match="Exact accepted"):
        AcceptedSource.root(fake)


def test_registered_forward_source_not_initial_root(actual, tmp_path):
    career, target = actual  # copied TEST-ONLY generation-one accepted registry.
    before = file_sha256(career.registry)
    source = AcceptedSource.career(career)
    assert source.checkpoint == career.identity()["checkpoint"]
    assert source.checkpoint != source.database_sha256
    assert source.database == (target / "checkpoint/payload/database.sqlite").resolve()
    assert file_sha256(career.registry) == before
    with sqlite3.connect(source.database) as c:
        c.execute("UPDATE world_info SET clock='2099-01-01'")
    with pytest.raises(ValueError, match="hash|provenance|tampered"):
        AcceptedSource.career(career)


def test_cross_year_dates_do_not_relabel_season(completed, policy):
    report = closure_report(completed, policy)
    assert report["ready_to_finalize"]  # 2027 matches actually played in January 2028.
    assert report["competitions"][0]["completed"] == 12
    policy["season"], policy["next_season"] = 2028, 2029
    assert not closure_report(completed, policy)["ready_to_finalize"]


def test_exact_retry_archive_and_portable_readonly_history(completed, tmp_path, policy):
    before = file_sha256(completed)
    rehearsal(completed, tmp_path, policy)
    directory = tmp_path / "rehearsal"
    for target in ("season_finalizing", "season_archived", "offseason_preparation"):
        request = str(uuid4())
        result = transition(directory, target, request_id=request)
        assert transition(directory, target, request_id=request) == result
        assert result["inherited_tables_unchanged"] and not result["acceptance_eligible"]
    with connect_read_only(directory / "season.sqlite") as c:
        assert c.execute("SELECT count(*) FROM season_archives").fetchone()[0] == 1
    restored = tmp_path / "restored"
    shutil.copytree(directory, restored)
    assert inspect_rehearsal(restored) == inspect_rehearsal(directory)
    with connect_read_only(restored / "parent.sqlite") as c:
        assert c.execute("SELECT count(*) FROM identity_evidence WHERE id IN (196,354)").fetchone()[0] == 2
    assert file_sha256(directory / "parent.sqlite") == before == file_sha256(completed)
    with pytest.raises(ValueError, match="not implemented"):
        transition(directory, "transfer_window", request_id=str(uuid4()))
    with pytest.raises(ValueError, match="activation"):
        transition(directory, "next_season_active", request_id=str(uuid4()))


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
def test_crash_preserves_exact_transition(completed, tmp_path, policy, stage):
    rehearsal(completed, tmp_path, policy)
    directory, request = tmp_path / "rehearsal", str(uuid4())
    with pytest.raises(RuntimeError, match="Injected season crash"):
        transition(directory, "season_finalizing", request_id=request, crash=stage)
    result = transition(directory, "season_finalizing", request_id=request)
    assert result["before"] == "season_in_progress"
    with connect_read_only(directory / "season.sqlite") as c:
        assert c.execute("SELECT count(*) FROM season_transitions").fetchone()[0] == 1
    with pytest.raises(ValueError, match="already bound"):
        transition(directory, "season_archived", request_id=request)


def test_concurrent_identical_requests_apply_once(completed, tmp_path, policy):
    rehearsal(completed, tmp_path, policy)
    directory, request = tmp_path / "rehearsal", str(uuid4())
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(transition, directory, "season_finalizing", request_id=request) for _ in range(2)]
        assert futures[0].result() == futures[1].result()
    with connect_read_only(directory / "season.sqlite") as c:
        assert c.execute("SELECT count(*) FROM season_transitions").fetchone()[0] == 1


def test_missing_scores_champions_and_payroll_block_closure(completed, policy):
    with sqlite3.connect(completed) as c:
        c.execute("UPDATE fixtures SET home_goals=NULL WHERE id=1")
        c.execute("DELETE FROM competition_history")
        c.execute("INSERT INTO world_obligations VALUES('payroll:2027-12','2027-12-31 23:59','scheduled')")
    result = closure_report(completed, policy)
    assert not result["ready_to_finalize"] and result["competitions"][0]["missing_scores"] == 1
    assert result["pending_obligations"] == ["payroll:2027-12"]


def test_unresolved_commitment_and_unscoped_competition_block(completed, policy):
    with sqlite3.connect(completed) as c:
        c.execute("CREATE TABLE world_batches(key TEXT PRIMARY KEY,status TEXT)")
        c.execute("INSERT INTO world_batches VALUES('committed','claimed')")
        c.execute("INSERT INTO fixtures VALUES(99,'Unknown cup 2027',NULL,'FINAL',1,2,NULL,NULL,'scheduled')")
    blockers = closure_report(completed, policy)["blockers"]
    assert "incomplete_execution_commitment" in blockers
    assert "unscoped_competition:unknown cup" in blockers


def test_cross_year_competition_retains_pending_identifiers(completed, policy):
    with sqlite3.connect(completed) as c:
        c.execute("UPDATE fixtures SET status='scheduled' WHERE id=1")
    policy["competitions"][0]["cross_year"] = True
    report = closure_report(completed, policy)
    assert report["ready_to_finalize"] and report["carried_cross_year"][0]["pending"] == ["fixtures:1"]
    policy["competitions"][0]["id"] = "MISSING"
    assert not closure_report(completed, policy)["ready_to_finalize"]


@pytest.mark.parametrize("change", ["parent", "journal", "policy", "state"])
def test_tampering_fails_closed(completed, tmp_path, policy, change):
    rehearsal(completed, tmp_path, policy)
    directory = tmp_path / "rehearsal"
    transition(directory, "season_finalizing", request_id=str(uuid4()))
    if change == "parent":
        with sqlite3.connect(directory / "parent.sqlite") as c:
            c.execute("UPDATE fixtures SET home_goals=99 WHERE id=1")
    elif change == "policy":
        marker = json.loads((directory / "rehearsal.json").read_text())
        marker["policy"]["competitions"][0]["minimum_completed"] = 1
        (directory / "rehearsal.json").write_text(json.dumps(marker))
    else:
        with sqlite3.connect(directory / "season.sqlite") as c:
            c.execute("UPDATE season_transitions SET previous_sha256='tampered'" if change == "journal"
                      else "UPDATE season_cycles SET state='season_archived'")
    with pytest.raises(ValueError):
        inspect_rehearsal(directory)


def test_duplicate_cycle_out_of_order_and_unsupported_policy(completed, tmp_path, policy):
    rehearsal(completed, tmp_path, policy)
    with pytest.raises(FileExistsError):
        rehearsal(completed, tmp_path, policy)
    with pytest.raises(ValueError, match="exact next"):
        transition(tmp_path / "rehearsal", "season_archived", request_id=str(uuid4()))
    policy["version"] = "unreviewed-2"
    with pytest.raises(ValueError, match="Unsupported"):
        closure_report(completed, policy)


def test_same_lifecycle_reusable_for_2028_to_2029(completed, tmp_path, policy):
    # Recorded miniature TEST season, not a claim of complete 2028 simulation.
    with sqlite3.connect(completed) as c:
        c.execute("UPDATE fixtures SET competition='Brasileirão 2028'")
        c.execute("UPDATE competition_history SET season=2028,competition='Brasileirão 2028'")
    policy["season"], policy["next_season"] = 2028, 2029
    report = rehearsal(completed, tmp_path, policy)
    assert report["season"] == 2028 and report["next_season"] == 2029
    assert transition(tmp_path / "rehearsal", "season_finalizing", request_id=str(uuid4()))["season"] == 2028


@pytest.mark.parametrize("year", [2028, 2029, 2030])
def test_generic_20_club_double_round_robin(year):
    clubs = [f"club:{i}" for i in range(1,21)]
    rows = double_round_robin(clubs, season=year)
    assert rows == double_round_robin(list(reversed(clubs)), season=year)
    assert len(rows) == len({r["key"] for r in rows}) == 380
    assert len({(r["home"],r["away"]) for r in rows}) == 380
    assert {r["round"] for r in rows} == set(range(1,39))
    for number in range(1,39):
        selected = [r for r in rows if r["round"] == number]
        assert len(selected) == 10
        assert len({k for r in selected for k in (r["home"],r["away"])}) == 20
    for club in clubs:
        assert sum(r["home"] == club for r in rows) == sum(r["away"] == club for r in rows) == 19
    assert all(r["kickoff"] is None and r["status"] == "undated_draft" for r in rows)


@pytest.mark.parametrize("clubs", [["a","b","c"], ["a","a","b","c"], [1,2,3,4]])
def test_schedule_rejects_bad_identities(clubs):
    with pytest.raises(ValueError):
        double_round_robin(clubs, season=2028)
