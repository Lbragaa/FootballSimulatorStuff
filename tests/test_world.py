"""Forward-world integration and hostile failure cases; all writes are disposable."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile

import pytest

from braga_era.acceptance import catalog
from braga_era.checkpoints import (
    restore_checkpoint,
    verify_checkpoint,
    verify_archive,
    promote_candidate,
    manifest_for,
    write_json,
)
from braga_era.db import connect_read_only, file_sha256
from braga_era.engine import EngineConfig, commit_seeds, prepare, simulate_match
from braga_era.history import digest
from braga_era.world import SCOPE
from braga_era.world.storage import (
    create,
    writer,
    transaction,
    logical_hash,
    process_lock,
)
from braga_era.world.runner import (
    advance,
    fixture_preview,
    narrate,
    claim,
    InjectedCrash,
    context,
)
from braga_era.world.reporting import preflight
from braga_era.world.rosters import distribution, stable_id, alias
from braga_era.world.players import projected, team_at
from braga_era.world.policy import WorldPolicy, Rules
from braga_era.world.adapters import adapter, ADAPTERS, recompute_standings
from braga_era.world.audit import audit
from braga_era.world.packages import export_world, fingerprints
from braga_era.world.knockout import resolve, validate_bundle


def clone(source, destination):
    destination.mkdir()
    for name in (
        "database.sqlite",
        "parent.sqlite",
        "world.json",
        "initialization_commitment.json",
    ):
        shutil.copyfile(source / name, destination / name)
    return destination


@pytest.fixture(scope="session")
def world_template(accepted_path, tmp_path_factory):
    directory = tmp_path_factory.mktemp("world-template") / "world"
    create(accepted_path, directory, "task03b-world-demo-v1")
    return directory


@pytest.fixture
def world(world_template, tmp_path):
    return clone(world_template, tmp_path / "world")


@pytest.fixture(scope="session")
def continental_world(world_template, tmp_path_factory):
    directory = clone(world_template, tmp_path_factory.mktemp("continental") / "world")
    advance(directory, before_fixture="league:332")
    return directory


@pytest.fixture(scope="session")
def played_world(continental_world, tmp_path_factory):
    directory = clone(continental_world, tmp_path_factory.mktemp("r26") / "world")
    advance(directory, until="2027-10-03 23:59")
    return directory


@pytest.fixture(scope="session")
def cup_world(played_world, tmp_path_factory):
    directory = clone(played_world, tmp_path_factory.mktemp("cups") / "world")
    advance(directory, until="2027-10-16 23:59")
    return directory


def test_all_missing_rosters_are_explicit_stable_and_eligible(world):
    with writer(world) as (c, policy):
        result = preflight(c, policy)
        assert result["passed"] and len(result["fixtures"]) == 16
        rows = distribution(c)
        assert len(rows) > 23
        assert len({r["depth"] for r in rows}) >= 3
        assert len({r["mean_ovr"] for r in rows}) > 10
        assert all(
            r["positions"]["GK"] == 3
            and 24 <= r["depth"] <= 28
            and not r["canonical_approval"]
            for r in rows
        )
        ids = [r[0] for r in c.execute("SELECT id FROM world_players")]
        assert len(set(ids)) == len(ids)
        assert (
            c.execute("SELECT min(id) FROM world_players WHERE modeled=1").fetchone()[0]
            > 1_000_000_000
        )
        for p in c.execute("SELECT * FROM world_players WHERE modeled=1"):
            assert json.loads(p["attributes_json"])["name"].startswith("Fictional ")
            assert not json.loads(p["provenance_json"])["canonical_approval"]
        assert alias("São Paulo") == alias("Sa\u0303o   Paulo")
        assert stable_id("x", 1) == stable_id("x", 1) != stable_id("y", 1)


def test_full_creation_is_logically_deterministic(world, accepted_path, tmp_path):
    other = tmp_path / "second"
    create(accepted_path, other, "task03b-world-demo-v1")
    with connect_read_only(world / "database.sqlite") as a, connect_read_only(
        other / "database.sqlite"
    ) as b:
        assert fingerprints(a) == fingerprints(b)


def test_all_four_namespaced_adapters(world):
    with writer(world) as (c, policy):
        assert set(ADAPTERS) == {"LEAGUE", "CDB", "LIB", "SULA"}
        keys = [r[0] for r in c.execute("SELECT key FROM world_fixtures")]
        assert len(keys) == len(set(keys)) and "league:333" in keys
        for comp in ADAPTERS:
            a = adapter(c, comp, policy)
            assert a.due_entries("2027-09-26")
            with pytest.raises(ValueError):
                a.fixture("missing:1")
        assert not adapter(c, "LEAGUE", policy).rules_for("league:333").penalties
        assert adapter(c, "CDB", policy).rules_for("cdb:QF-01:L2").penalties
        with pytest.raises(ValueError, match="dependency"):
            adapter(c, "LIB", policy).pregame("lib:LIB-R16-01:L2")
        with pytest.raises(ValueError, match="qualifier"):
            adapter(c, "CDB", policy).pregame("cdb:SF-01:L1")


@pytest.mark.parametrize("extra_time", [False, True])
def test_aggregate_draw_extra_time_and_penalties(world, extra_time):
    with writer(world) as (c, policy):
        s = adapter(c, "LIB", policy).pregame("lib:LIB-R16-01:L1", logical_hash(c))
    cfg = EngineConfig()
    seeds = commit_seeds(s, cfg, "knockout-unit")
    r = simulate_match(s, prepare(s, cfg, seeds), cfg, seeds)
    prior = (max(0, r.score[1] - r.score[0]), max(0, r.score[0] - r.score[1]))
    rules = Rules("LIB", extra_time=extra_time, penalties=True)
    bundle = resolve(s, r, cfg, rules, prior)
    assert validate_bundle(s, r, cfg, rules, prior, bundle)["ok"]
    assert bundle["resolution"]["winner"] in (s.home.key, s.away.key)
    assert bundle["resolution"]["extra_time_played"] == extra_time
    if not extra_time:
        assert bundle["resolution"]["penalty_score"] is not None
        assert bundle["score"] == list(
            r.score
        )  # shootout kicks never count as match goals
        assert bundle["resolution"]["kicks"]
    else:
        assert any(e["kind"] == "EXTRA_TIME_START" for e in bundle["events"])
    assert bundle["events"][-1]["kind"] == "FINAL_WHISTLE"
    bad = json.loads(json.dumps(bundle))
    bad["score"][0] += 1
    with pytest.raises(ValueError):
        validate_bundle(s, r, cfg, rules, prior, bad)
    with pytest.raises(ValueError):
        resolve(s, r, cfg, replace(rules, away_goals=True), prior)


def test_simultaneous_inputs_and_exactly_once_receipts(continental_world):
    with writer(continental_world) as (c, policy):
        validation = audit(c, continental_world / "parent.sqlite")
        assert validation["continental_final"] == 16
        assert c.execute("SELECT count(*) FROM world_batches").fetchone()[0] == 1
        sources = [
            json.loads(r[0])["snapshot"]["source_sha256"]
            for r in c.execute("SELECT input_json FROM world_executions")
        ]
        assert len(set(sources)) == 1
        assert (
            c.execute("SELECT clock FROM world_info").fetchone()[0]
            == "2027-09-30 23:59"
        )
        assert c.execute("SELECT count(*) FROM world_receipts").fetchone()[0] == 16
        f = c.execute(
            "SELECT * FROM world_fixtures WHERE status='final' LIMIT 1"
        ).fetchone()
        with pytest.raises(ValueError):
            claim(c, [f], policy)
        with pytest.raises(ValueError):
            adapter(c, f["competition"], policy).pregame(f["key"])


def test_cross_competition_state_flows_and_overlapping_matches(played_world):
    with writer(played_world) as (c, policy):
        validation = audit(c, played_world / "parent.sqlite")
        assert validation["receipts"] == 26 and validation["league_final"] == 10
        # 18:00 starts before the 19:00 kickoff, but finishes at 19:33; 19:00 inputs exclude that unfinished result.
        a = c.execute(
            "SELECT * FROM world_batches WHERE kickoff='2027-10-03 18:00'"
        ).fetchone()
        b = c.execute(
            "SELECT * FROM world_batches WHERE kickoff='2027-10-03 19:00'"
        ).fetchone()
        assert b["kickoff"] < a["finish_time"] < b["finish_time"]
        before = json.loads(
            c.execute(
                "SELECT input_json FROM world_executions WHERE fixture_key='league:333'"
            ).fetchone()[0]
        )["snapshot"]
        perf = {
            r["player_id"]: json.loads(r["performance_json"])
            for r in c.execute(
                "SELECT * FROM world_performances WHERE fixture_key='lib:LIB-R16-01:L1'"
            )
        }
        carried = 0
        for p in before["home"]["players"]:
            if p["id"] in perf:
                assert p["form"] == perf[p["id"]]["form_after"]
                assert p["fitness"] >= perf[p["id"]]["fitness_after"]
                carried += 1
        assert carried >= 11
        assert c.execute("SELECT count(*) FROM players").fetchone()[0] == 547
        assert all(
            "196"
            not in [
                str(pid)
                for pid in json.loads(r[0])["regulation"]["plans"][0]["starters"]
            ]
            for r in c.execute("SELECT result_json FROM world_executions")
        )


def test_elapsed_recovery_not_per_match():
    p = WorldPolicy()
    base = {
        "fitness": 50,
        "observed_at": "2027-09-26 12:00",
        "injury_until": "2027-09-27 12:00",
    }
    assert projected(base, "2027-09-28 12:00", p)["fitness"] == 53
    assert projected(base, "2027-09-28 12:00", p)["injury_until"] is None
    interim = projected(base, "2027-09-27 12:00", p)
    interim["observed_at"] = "2027-09-27 12:00"
    assert projected(interim, "2027-09-28 12:00", p)["fitness"] == 53
    with pytest.raises(ValueError):
        projected(base, "2027-09-25 12:00", p)


def test_suspension_registration_injury_and_training_exclusions(world):
    with writer(world) as (c, p):
        s = adapter(c, "LEAGUE", p).pregame("league:332", logical_hash(c))
        pid = next(x.id for x in s.away.players if x.eligible)
        c.execute("INSERT INTO world_discipline VALUES(?,?,?,?)", (pid, "LEAGUE", 0, 1))
        league = team_at(c, s.away.key, "LEAGUE", s.kickoff, p)
        assert not next(x for x in league.players if x.id == pid).eligible
        cup = team_at(c, s.away.key, "LIB", s.kickoff, p)
        assert next(x for x in cup.players if x.id == pid).eligible
        row = json.loads(
            c.execute(
                "SELECT state_json FROM world_player_state WHERE player_id=?", (pid,)
            ).fetchone()[0]
        )
        for changes, reason in [
            ({"registered": False}, "registered"),
            ({"contract_end": "2027-09-01"}, "expired"),
            ({"injury_until": "2027-10-09 12:00"}, "injury"),
        ]:
            updated = {**row, **changes}
            c.execute(
                "UPDATE world_player_state SET state_json=? WHERE player_id=?",
                (json.dumps(updated), pid),
            )
            selected = next(
                x
                for x in team_at(c, s.away.key, "SULA", s.kickoff, p).players
                if x.id == pid
            )
            assert not selected.eligible and any(
                reason in x for x in selected.exclusion_reasons
            )
        assert not next(
            x
            for x in team_at(c, "club:5", "LEAGUE", s.kickoff, p).players
            if x.id == 196
        ).eligible
        assert next(
            x
            for x in team_at(c, "club:5", "LEAGUE", s.kickoff, p).players
            if x.id == 354
        ).eligible
        # Force new forward injuries and reds, then verify the shared persistence layer.
        from braga_era.world.players import apply_players

        f = c.execute(
            "SELECT * FROM world_fixtures WHERE key='lib:LIB-R16-01:L1'"
        ).fetchone()
        snap = adapter(c, "LIB", p).pregame(f["key"], logical_hash(c))
        cfg = replace(
            EngineConfig(),
            injury_probability_per_match=1,
            straight_red_probability_per_team=1,
        )
        seeds = commit_seeds(snap, cfg, "forced-persistent-medical-discipline")
        result = simulate_match(snap, prepare(snap, cfg, seeds), cfg, seeds)
        bundle = resolve(snap, result, cfg, Rules("LIB"))
        apply_players(c, f, snap, bundle, p)
        injuries = [x for x in bundle["performances"] if x["injured"]]
        assert len(injuries) == 1
        state = json.loads(
            c.execute(
                "SELECT state_json FROM world_player_state WHERE player_id=?",
                (injuries[0]["player_id"],),
            ).fetchone()[0]
        )
        assert (
            state["injury_until"] and state["fitness"] == injuries[0]["fitness_after"]
        )
        for row in (x for x in bundle["performances"] if x["red"]):
            assert (
                c.execute(
                    "SELECT bans FROM world_discipline WHERE player_id=? AND competition='LIB'",
                    (row["player_id"],),
                ).fetchone()[0]
                >= 1
            )


@pytest.mark.parametrize(
    "stage",
    [
        "after_claim",
        "after_result",
        "after_simulation",
        "during_apply",
        "before_commit",
        "after_commit",
    ],
)
def test_crash_resumption_keeps_original_inputs_and_results(
    world, continental_world, stage
):
    with pytest.raises(InjectedCrash):
        advance(world, until="2027-09-30 23:59", crash=stage)
    with connect_read_only(world / "database.sqlite") as c:
        commitments = {
            r["fixture_key"]: (r["input_sha256"], r["seed_json"])
            for r in c.execute("SELECT * FROM world_executions")
        }
        if stage in ("during_apply", "before_commit"):
            assert c.execute("SELECT count(*) FROM world_receipts").fetchone()[0] == 0
    advance(world, until="2027-09-30 23:59")
    with connect_read_only(world / "database.sqlite") as c, connect_read_only(
        continental_world / "database.sqlite"
    ) as expected:
        assert commitments == {
            r["fixture_key"]: (r["input_sha256"], r["seed_json"])
            for r in c.execute("SELECT * FROM world_executions")
        }
        assert fingerprints(c) == fingerprints(expected)


def test_real_process_crash_releases_lock_and_resumes(world):
    script = "import os; from pathlib import Path; from braga_era.world import runner; runner.fault=lambda requested,stage: os._exit(73) if stage=='after_claim' else None; runner.advance(Path(__import__('sys').argv[1]),until='2027-09-30 23:59')"
    done = subprocess.run(
        [sys.executable, "-c", script, str(world)], capture_output=True, text=True
    )
    assert done.returncode == 73, done.stderr
    result = advance(world, until="2027-09-30 23:59")
    assert result["continental_final"] == 16


def test_concurrent_runners_are_rejected(world):
    script = "from braga_era.world.runner import advance; advance(__import__('sys').argv[1],until='2027-09-30 23:59')"
    with process_lock(world):
        result = subprocess.run(
            [sys.executable, "-c", script, str(world)], capture_output=True, text=True
        )
        assert result.returncode != 0 and "process lock" in result.stderr
    assert advance(world, until="2027-09-30 23:59")["receipts"] == 16


def test_no_fresh_draws_when_resuming_applied_world(
    played_world, tmp_path, monkeypatch
):
    target = clone(played_world, tmp_path / "repeated")

    def fail(*args, **kwargs):
        raise AssertionError("An applied match was rerolled")

    monkeypatch.setattr("braga_era.world.runner.simulate_match", fail)
    with connect_read_only(target / "database.sqlite") as c:
        before = fingerprints(c)
    assert advance(target, until="2027-10-03 23:59")["groups_this_call"] == 0
    with connect_read_only(target / "database.sqlite") as c:
        assert fingerprints(c) == before


def test_payroll_is_exactly_once_and_financial_authority_is_preserved(
    played_world, tmp_path
):
    target = clone(played_world, tmp_path / "payroll")
    from braga_era.payroll import book_payroll

    with writer(target) as (c, p):
        period = c.execute(
            "SELECT * FROM payroll_periods WHERE period='2027-09'"
        ).fetchone()
        assert (
            period["cash_cents"] == period["amount_due_cents"]
            and period["ledger_id"] is not None
        )
        cash = c.execute("SELECT sum(amount_brl) FROM finance_ledger").fetchone()[0]
        with transaction(c, "idempotent-payroll-test"):
            assert (
                book_payroll(c, "2027-09", period["amount_due_cents"], "2027-09-30")[1]
                is False
            )
        assert (
            c.execute("SELECT sum(amount_brl) FROM finance_ledger").fetchone()[0]
            == cash
        )
        assert audit(c, target / "parent.sqlite")["ok"]


def test_native_cup_legs_aggregates_qualification_and_bracket_activation(cup_world):
    with writer(cup_world) as (c, p):
        assert audit(c, cup_world / "parent.sqlite")["ok"]
        assert (
            c.execute(
                "SELECT count(*) FROM world_ties WHERE competition='CDB' AND status='final'"
            ).fetchone()[0]
            == 4
        )
        assert (
            c.execute(
                "SELECT count(*) FROM cdb_2027_legs WHERE tie_code LIKE 'QF-%'"
            ).fetchone()[0]
            == 8
        )
        assert (
            c.execute(
                "SELECT count(*) FROM world_ties WHERE competition IN ('LIB','SULA') AND winner IS NOT NULL"
            ).fetchone()[0]
            == 16
        )
        semis = c.execute(
            "SELECT * FROM cdb_2027_bracket WHERE stage='Semifinais'"
        ).fetchall()
        assert len(semis) == 2 and all(
            r["club_a"] and r["club_b"] and r["status"] == "scheduled" for r in semis
        )
        assert (
            c.execute(
                "SELECT count(*) FROM world_fixtures WHERE competition IN ('LIB','SULA') AND status='conditional'"
            ).fetchone()[0]
            > 0
        )


def test_unresolved_draw_fails_closed_without_skipping(cup_world, tmp_path):
    target = clone(cup_world, tmp_path / "unresolved")
    with pytest.raises(ValueError, match="Unresolved qualifier/draw"):
        advance(target, until="2027-10-22 23:59")
    with connect_read_only(target / "database.sqlite") as c:
        unresolved = c.execute(
            "SELECT min(kickoff) FROM world_fixtures WHERE status='conditional'"
        ).fetchone()[0]
        assert c.execute("SELECT clock FROM world_info").fetchone()[0] < unresolved


@pytest.mark.parametrize(
    "tamper", ["history", "calendar", "finance", "schema", "journal", "player"]
)
def test_world_audit_rejects_tampering(world, tamper):
    with writer(world) as (c, p):
        if tamper == "history":
            c.execute("UPDATE fixtures SET home_goals=99 WHERE id=322")
        if tamper == "calendar":
            c.execute(
                "UPDATE fixtures SET datetime_local='2028-01-01 00:00' WHERE id=332"
            )
        if tamper == "finance":
            c.execute("UPDATE finance_budget SET amount_brl=99999999 WHERE id=1")
        if tamper == "schema":
            c.execute("CREATE TABLE unexpected(id INTEGER)")
        if tamper == "journal":
            c.execute("UPDATE world_operations SET sha256='wrong' WHERE sequence=1")
        if tamper == "player":
            c.execute("UPDATE players SET ovr=99 WHERE id=1")
        with pytest.raises(ValueError):
            audit(c, world / "parent.sqlite")


def test_identity_constraints_and_overlapping_fixture_rejection(world):
    with writer(world) as (c, p):
        row = c.execute("SELECT * FROM world_players LIMIT 1").fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO world_players VALUES(?,?,?,?,?,?)", tuple(row))
        fixtures = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM world_fixtures WHERE kickoff='2027-09-30 16:00' ORDER BY key LIMIT 2"
            )
        ]
        fixtures[1]["home"] = fixtures[0]["home"]
        with pytest.raises(ValueError, match="overlapping"):
            claim(c, fixtures, p)


def test_parent_mismatch_unsupported_policy_and_source_guard(
    world, canonical_path, tmp_path
):
    with pytest.raises(ValueError, match="exact accepted"):
        create(canonical_path, tmp_path / "rejected", "x")
    with pytest.raises(ValueError, match="Unsupported"):
        replace(WorldPolicy(), version="unreviewed").validate()
    (world / "parent.sqlite").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="parent hash"):
        advance(world, until="2027-09-30 23:59")


def test_portable_development_checkpoint_and_cursor(played_world, tmp_path):
    target = clone(played_world, tmp_path / "export-source")
    archive = tmp_path / "world.zip"
    first = narrate(target, "league:332")
    assert first["events"][0]["kind"] == "KICKOFF" and "postmatch_summary" not in first
    export_world(target, archive)
    destination = tmp_path / "restored"
    verified = restore_checkpoint(archive, destination)
    assert verified["independent_replay"] and not verified["acceptance_eligible"]
    next_event = narrate(destination, "league:332")
    assert (
        next_event["events"][0]["sequence"] == 2
        and "postmatch_summary" not in next_event
    )
    while not next_event["postmatch_available"]:
        next_event = narrate(destination, "league:332", 20)
    assert "postmatch_summary" in next_event
    with pytest.raises(ValueError):
        promote_candidate(
            destination,
            tmp_path / "canonical.json",
            expected_parent_sha256=catalog()["database_sha256"],
            approved_candidate_sha256=file_sha256(destination / "database.sqlite"),
            approvals=[],
        )


def test_tampered_and_malformed_world_packages(played_world, tmp_path):
    target = clone(played_world, tmp_path / "source")
    archive = tmp_path / "good.zip"
    export_world(target, archive)
    folder = tmp_path / "restored"
    restore_checkpoint(archive, folder)
    metadata = json.loads((folder / "checkpoint.json").read_text())
    metadata["save_version"] = "047"
    write_json(folder / "checkpoint.json", metadata)
    write_json(folder / "manifest.json", manifest_for(folder))
    with pytest.raises(ValueError):
        verify_checkpoint(folder)
    bad = tmp_path / "traversal.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../outside", "no")
    with pytest.raises(ValueError):
        restore_checkpoint(bad, tmp_path / "bad-restore")


def test_fresh_installation_never_silently_uses_original_046(monkeypatch, tmp_path):
    from braga_era import config

    monkeypatch.setattr(config, "__file__", str(tmp_path / "braga_era/config.py"))
    monkeypatch.setenv("BRAGA_ERA_REGISTRY", str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError, match="Accepted 046C"):
        config.database_path()


def test_original_accepted_and_parent_bytes_remain_unchanged(
    accepted_path, canonical_path
):
    assert file_sha256(accepted_path) == catalog()["database_sha256"]
    assert file_sha256(canonical_path) == catalog()["parent_sha256"]


def test_unsupported_committed_engine_fails_before_draws(world, monkeypatch):
    with pytest.raises(InjectedCrash):
        advance(world, until="2027-09-30 23:59", crash="after_claim")
    with writer(world) as (c, p):
        config = asdict(EngineConfig())
        config["version"] = "unreviewed"
        with transaction(c, "tamper-config-test"):
            c.execute(
                "UPDATE world_executions SET config_json=?", (json.dumps(config),)
            )

    def fail(*args, **kwargs):
        raise AssertionError("Unsupported model reached RNG execution")

    monkeypatch.setattr("braga_era.world.runner.prepare", fail)
    with pytest.raises(ValueError, match="Unsupported engine"):
        advance(world, until="2027-09-30 23:59")


def test_incomplete_batch_cannot_be_packaged(world, tmp_path):
    with pytest.raises(InjectedCrash):
        advance(world, until="2027-09-30 23:59", crash="after_result")
    with pytest.raises(ValueError, match="Resume the committed batch"):
        export_world(world, tmp_path / "incomplete.zip")
    assert not (tmp_path / "incomplete.zip").exists()


def test_training_effects_are_consumed_once_for_both_clubs(world):
    with writer(world) as (c, p):
        f = c.execute(
            "SELECT * FROM world_fixtures WHERE key='lib:LIB-R16-01:L1'"
        ).fetchone()
        original = team_at(c, f["home"], "LIB", f["kickoff"], p).strength
        with transaction(c, "explicit-test-training"):
            for index, key in enumerate((f["home"], f["away"])):
                c.execute(
                    "INSERT INTO world_training VALUES(?,?,?,?,?,?)",
                    (
                        f"effect-{index}",
                        key,
                        "2027-09-29 00:00",
                        "2027-10-01 00:00",
                        0.5,
                        None,
                    ),
                )
        assert team_at(c, f["home"], "LIB", f["kickoff"], p).strength == original + 0.5
    advance(world, until="2027-09-30 23:59")
    with writer(world) as (c, p):
        assert {
            r[0] for r in c.execute("SELECT consumed_fixture FROM world_training")
        } == {"lib:LIB-R16-01:L1"}
        assert team_at(c, f["home"], "LIB", "2027-10-06 16:00", p).strength == original


def test_exact_minute_completion_boundary_and_no_clock_rewind(world):
    result = advance(world, until="2027-09-30 17:33")
    assert result["receipts"] == 16
    with pytest.raises(ValueError, match="predates"):
        advance(world, until="2027-09-29 23:59")


def test_tampered_world_database_cannot_be_authorized_by_resealing_manifest(
    played_world, tmp_path
):
    target = clone(played_world, tmp_path / "source-reseal")
    archive = tmp_path / "reseal.zip"
    export_world(target, archive)
    restored = tmp_path / "resealed"
    restore_checkpoint(archive, restored)
    with sqlite3.connect(restored / "database.sqlite") as c:
        c.execute("UPDATE fixtures SET home_goals=99 WHERE id=322")
    metadata = json.loads((restored / "checkpoint.json").read_text())
    metadata["database_sha256"] = file_sha256(restored / "database.sqlite")
    write_json(restored / "checkpoint.json", metadata)
    write_json(restored / "manifest.json", manifest_for(restored))
    with pytest.raises(ValueError, match="completed record"):
        verify_checkpoint(restored)


def test_generic_inspection_cannot_mislabel_development_as_accepted(
    played_world, capsys
):
    from braga_era.cli import main

    assert (
        main(["inspect", "--db", str(played_world / "database.sqlite"), "--json"]) == 0
    )
    state = json.loads(capsys.readouterr().out)
    assert (
        state["save_version"] == "DEV-03B"
        and state["scope"] == SCOPE
        and not state["promotable"]
    )
    assert "vasco" not in state and "standings" not in state and "score" not in state
    assert main(["audit", "--db", str(played_world / "database.sqlite"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert (
        main(
            [
                "audit",
                "--db",
                str(played_world / "database.sqlite"),
                "--profile",
                "046C",
                "--json",
            ]
        )
        == 1
    )
    assert not json.loads(capsys.readouterr().out)["ok"]
