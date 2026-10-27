"""Forward policy, draws, mixed configurations and commissioner gate regressions."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import sqlite3

import pytest
from braga_era.world.storage import create, writer, logical_hash, transaction
from braga_era.world.policy import ReadinessPolicy, WorldPolicy, Rules, load_policy
from braga_era.world.runner import context, claim, advance, InjectedCrash
from braga_era.world.forward_config import configuration
from braga_era.world.knockout_v2 import resolve, validate_bundle
from braga_era.world.progression import pairings
from braga_era.world.audit import audit
from braga_era.engine import commit_seeds, prepare, simulate_match
from braga_era.db import connect_read_only
from braga_era.history import digest
from braga_era import forward


@pytest.fixture(scope="module")
def readiness_template(accepted_path, tmp_path_factory):
    path = tmp_path_factory.mktemp("readiness") / "world"
    create(accepted_path, path, "test-readiness-v1", ReadinessPolicy())
    return path


@pytest.fixture
def ready(readiness_template, tmp_path):
    path = tmp_path / "world"
    shutil.copytree(readiness_template, path)
    return path


def test_v1_rosters_identical_and_forward_policy_separate(
    ready, accepted_path, tmp_path
):
    old = tmp_path / "v1"
    create(accepted_path, old, "different-match-seed", WorldPolicy())
    with writer(ready) as (c, p), connect_read_only(old / "database.sqlite") as v1:
        assert isinstance(p, ReadinessPolicy)
        for table in ("world_clubs", "world_players", "world_player_state"):
            assert [tuple(r) for r in c.execute("SELECT * FROM " + table)] == [
                tuple(r) for r in v1.execute("SELECT * FROM " + table)
            ]
        assert audit(c, ready / "parent.sqlite")["ok"]
    with pytest.raises(ValueError):
        load_policy({**asdict(ReadinessPolicy()), "version": "unsupported"})


def test_each_simultaneous_fixture_commits_its_own_configuration(ready):
    with writer(ready) as (c, p):
        fixtures = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM world_fixtures WHERE kickoff='2027-09-30 16:00' ORDER BY key LIMIT 2"
            )
        ]
        # Two disjoint clubs in a neutral final and a regular semifinal, at one kickoff.
        with transaction(c, "synthetic-mixed-final-test"):
            fixtures[0]["stage"] = "Final única"
            c.execute(
                "UPDATE world_fixtures SET stage='Final única' WHERE key=?",
                (fixtures[0]["key"],),
            )
        claim(c, fixtures, p)
        rows = c.execute(
            "SELECT * FROM world_executions ORDER BY fixture_key"
        ).fetchall()
        for row in rows:
            data = json.loads(row["input_json"])
            config = json.loads(row["config_json"])
            seed = json.loads(row["seed_json"])
            assert digest(config) == seed["config_sha256"]
            assert config["neutral_final"] == data["rules"]["extra_time"]


def test_committed_draws_are_deterministic_seeded_and_unique():
    inputs = {
        "seed_sha256": "a" * 64,
        "qualifiers": list("abcdefghijklmnop"),
        "seeded": list("abcdefgh"),
    }
    pairs = pairings(inputs)
    assert pairs == pairings(inputs)
    assert sorted(p for pair in pairs for p in pair) == list("abcdefghijklmnop")
    assert all(a not in inputs["seeded"] and b in inputs["seeded"] for a, b in pairs)
    with pytest.raises(ValueError):
        pairings({**inputs, "qualifiers": ["a", "a"]})


def test_draw_commit_crash_resumes_without_new_seed_or_duplicate_ties(
    ready, monkeypatch
):
    from braga_era.world import progression

    with writer(ready) as (c, p):
        # Synthetic prospective qualifiers on a disposable test fixture; no legacy rows change.
        c.execute(
            "UPDATE world_ties SET winner=club_a,status='final' WHERE competition='LIB' AND stage='R16'"
        )
        c.execute(
            "UPDATE world_fixtures SET status='final' WHERE competition='LIB' AND stage='R16'"
        )
        original = progression.pairings

        def crash(*args):
            raise RuntimeError("crash after draw commitment")

        monkeypatch.setattr(progression, "pairings", crash)
        with pytest.raises(RuntimeError, match="draw commitment"):
            progression.activate(c)
        committed = c.execute(
            "SELECT commitment_json FROM world_draws WHERE key='LIB:QF'"
        ).fetchone()[0]
        monkeypatch.setattr(progression, "pairings", original)
        progression.activate(c)
        assert (
            c.execute(
                "SELECT commitment_json FROM world_draws WHERE key='LIB:QF'"
            ).fetchone()[0]
            == committed
        )
        assert (
            c.execute(
                "SELECT count(*) FROM world_fixtures WHERE key LIKE 'lib:QF-%'"
            ).fetchone()[0]
            == 8
        )
        progression.activate(c)
        assert (
            c.execute(
                "SELECT count(*) FROM world_fixtures WHERE key LIKE 'lib:QF-%'"
            ).fetchone()[0]
            == 8
        )


def test_extended_extra_time_accounting_and_shootout(ready):
    with writer(ready) as (c, p):
        f = c.execute("SELECT * FROM world_fixtures WHERE key='league:333'").fetchone()
        snap, _, _ = context(c, f, p, logical_hash(c))
        cfg = configuration(p)
    for i in range(8):
        seeds = commit_seeds(snap, cfg, "test-ET-v2:" + str(i))
        reg = simulate_match(snap, prepare(snap, cfg, seeds), cfg, seeds)
        prior = reg.score[
            ::-1
        ]  # force an aggregate tie without editing a generated result
        rules = Rules("LIB", extra_time=True, penalties=True)
        bundle = resolve(snap, reg, cfg, rules, prior)
        assert validate_bundle(snap, reg, cfg, rules, prior, bundle)[
            "independent_extension_accounting"
        ]
        assert bundle["resolution"]["extra_time_played"]
        assert any(e["kind"] == "EXTRA_TIME_INTERVAL" for e in bundle["events"])
        assert sum(s["goal"] for s in bundle["shots"]) == sum(bundle["score"])
        for key in (snap.home.key, snap.away.key):
            assert (
                sum(
                    e["kind"] == "SUBSTITUTION" and e["club_key"] == key
                    for e in bundle["events"]
                )
                <= 6
            )
        assert sum(p["seconds_played"] for p in bundle["performances"]) <= 22 * (
            reg.duration_seconds + 1800
        )
        tampered = json.loads(json.dumps(bundle))
        tampered["performances"][0]["seconds_played"] += 1
        with pytest.raises(ValueError):
            validate_bundle(snap, reg, cfg, rules, prior, tampered)


def test_blob_corruption_and_hash_chain_are_rejected(ready):
    with writer(ready) as (c, p):
        c.execute(
            "UPDATE world_blobs SET value_json='null' WHERE sha256=(SELECT min(sha256) FROM world_blobs)"
        )
        with pytest.raises(ValueError, match="blob"):
            audit(c, ready / "parent.sqlite")


def test_et_goalkeeper_dismissal_injury_and_penalty_eligibility(ready, monkeypatch):
    import random
    from braga_era.world import knockout_v2

    with writer(ready) as (c, p):
        f = c.execute("SELECT * FROM world_fixtures WHERE key='league:333'").fetchone()
        snapshot, _, _ = context(c, f, p, logical_hash(c))
        cfg = configuration(p)
    seeds = commit_seeds(snapshot, cfg, "forced-ET-medical-discipline")
    reg = simulate_match(snapshot, prepare(snapshot, cfg, seeds), cfg, seeds)
    players = {p.id: p for t in (snapshot.home, snapshot.away) for p in t.players}

    class Forced(random.Random):
        def random(self):
            return 0.0

        def choice(self, ids):
            return max(ids, key=lambda pid: (players[pid].position == "GK", -pid))

    monkeypatch.setattr(knockout_v2, "stream", lambda *args: Forced(7))
    bundle = resolve(
        snapshot,
        reg,
        cfg,
        Rules("LIB", extra_time=True, penalties=True),
        reg.score[::-1],
    )
    assert any(
        e["kind"] == "INJURY" and e["period"].startswith("ET") for e in bundle["events"]
    )
    assert any(
        e["kind"] == "RED_CARD"
        and e["period"].startswith("ET")
        and players[e["player_id"]].position == "GK"
        for e in bundle["events"]
    )
    blocked = {
        p["player_id"] for p in bundle["performances"] if p["injured"] or p["red"]
    }
    assert all(k["player_id"] not in blocked for k in bundle["resolution"]["kicks"])
    assert validate_bundle(
        snapshot,
        reg,
        cfg,
        Rules("LIB", extra_time=True, penalties=True),
        reg.score[::-1],
        bundle,
    )["ok"]


def test_hikari_cannot_jump_to_future_match_or_table(ready):
    from braga_era.gameplay import handoff
    from braga_era.world.runner import narrate

    before = handoff(ready, "table")
    advance(ready, until="2027-09-30 23:59")
    assert handoff(ready, "table") == before
    next_events = handoff(ready, "next")
    assert all(e["kickoff"] == "2027-09-30 16:00" for e in next_events["events"])
    with pytest.raises(ValueError, match="earlier chronological"):
        handoff(ready, "preview", "league:332")
    key = next_events["events"][0]["key"]
    page = handoff(ready, "narrate", key)
    assert "postmatch_summary" not in page and page["events"][0]["kind"] == "KICKOFF"
    with writer(ready) as (c, p):
        c.execute("UPDATE world_cursors SET sequence=99999 WHERE fixture_key=?", (key,))
    with pytest.raises(ValueError, match="cursor"):
        narrate(ready, key)


def test_new_month_payroll_is_idempotent_and_rolls_back_on_failure(ready):
    from braga_era.world.runner import apply_obligation

    with writer(ready) as (c, p):
        item = dict(
            c.execute(
                "SELECT * FROM world_obligations WHERE key='payroll:2027-10'"
            ).fetchone()
        )
        apply_obligation(c, item, ready / "parent.sqlite")
        count = c.execute("SELECT count(*) FROM finance_ledger").fetchone()[0]
        apply_obligation(c, item, ready / "parent.sqlite")
        assert c.execute("SELECT count(*) FROM finance_ledger").fetchone()[0] == count
        assert (
            c.execute(
                "SELECT count(*) FROM payroll_obligations WHERE period='2027-10'"
            ).fetchone()[0]
            > 0
        )
        assert audit(c, ready / "parent.sqlite")["ok"]


def manifest_for(ready, accepted_path):
    with connect_read_only(ready / "database.sqlite") as c:
        fixtures = [
            r[0]
            for r in c.execute(
                "SELECT key FROM world_fixtures WHERE kickoff='2027-09-30 16:00' ORDER BY key"
            )
        ]
    return forward.prepare(
        accepted_path,
        until="2027-09-30 17:33",
        fixtures=fixtures,
        seed="rehearsal-only-never-use-officially",
        execution_id="gate-test-1",
    )


def test_gate_requires_separate_signed_execution_and_exact_hash_acceptance(
    ready, accepted_path, tmp_path
):
    key = b"test-only-authority-key-32-bytes!!"
    registry = tmp_path / "authority" / "test.sqlite"
    forward.provision(
        registry, key, test_only=True, commissioner="SIMULATED TEST COMMISSIONER"
    )
    manifest = manifest_for(ready, accepted_path)
    decision = {
        "action": "authorize_execution",
        "manifest_sha256": digest(manifest),
        "approvals": sorted(forward.REQUIRED),
        "commissioner": "SIMULATED TEST COMMISSIONER",
        "test_only": True,
    }
    with pytest.raises(ValueError):
        forward.authorize(
            registry,
            key,
            manifest,
            {**decision, "approvals": ["rosters"]},
            forward.sign(key, decision),
        )
    forward.authorize(registry, key, manifest, decision, forward.sign(key, decision))
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        forward.authorize(
            registry, key, manifest, decision, forward.sign(key, decision)
        )
    conflicting = {
        **manifest,
        "execution_id": "different-id-same-fixtures",
        "seed": "another-root",
    }
    conflicting_decision = {**decision, "manifest_sha256": digest(conflicting)}
    with pytest.raises(sqlite3.IntegrityError):
        forward.authorize(
            registry,
            key,
            conflicting,
            conflicting_decision,
            forward.sign(key, conflicting_decision),
        )
    target = tmp_path / "candidate"
    with pytest.raises(InjectedCrash):
        forward.execute(
            registry,
            key,
            manifest["execution_id"],
            target,
            accepted_path,
            crash="after_result",
        )
    result = forward.execute(
        registry, key, manifest["execution_id"], target, accepted_path
    )
    assert result["test_only"] and result["independent_restoration"]
    acceptance = {
        "action": "accept_forward_candidate",
        "candidate_sha256": result["candidate_sha256"],
        "parent_sha256": manifest["parent_sha256"],
        "commissioner": "SIMULATED TEST COMMISSIONER",
        "test_only": True,
    }
    with pytest.raises(ValueError):
        forward.promote(target, registry, key, decision, forward.sign(key, decision))
    assert forward.promote(
        target, registry, key, acceptance, forward.sign(key, acceptance)
    )["test_only"]
    with pytest.raises(ValueError):
        forward.execute(registry, key, manifest["execution_id"], target, accepted_path)


def test_wrong_gate_parent_key_policy_and_fixture_inventory(
    ready, accepted_path, tmp_path
):
    key = b"other-test-key-at-least-32-bytes!!"
    registry = tmp_path / "trust" / "r.sqlite"
    forward.provision(registry, key, test_only=True, commissioner="SIMULATED")
    manifest = manifest_for(ready, accepted_path)
    decision = {
        "action": "authorize_execution",
        "manifest_sha256": digest(manifest),
        "approvals": sorted(forward.REQUIRED),
        "commissioner": "SIMULATED",
        "test_only": True,
    }
    with pytest.raises(ValueError):
        forward.authorize(
            registry, b"x" * 32, manifest, decision, forward.sign(key, decision)
        )
    bad = {**manifest, "policy": asdict(WorldPolicy())}
    bad_decision = {**decision, "manifest_sha256": digest(bad)}
    with pytest.raises(ValueError):
        forward.authorize(
            registry, key, bad, bad_decision, forward.sign(key, bad_decision)
        )
    incomplete = {**manifest, "fixtures": manifest["fixtures"][:-1]}
    approval = {**decision, "manifest_sha256": digest(incomplete)}
    forward.authorize(registry, key, incomplete, approval, forward.sign(key, approval))
    with pytest.raises(ValueError, match="exact chronological"):
        forward.execute(
            registry,
            key,
            manifest["execution_id"],
            tmp_path / "bad-batch",
            accepted_path,
        )
