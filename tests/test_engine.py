"""Forward engine invariants and failure cases using the exact accepted bytes."""

from dataclasses import FrozenInstanceError, replace
import json
import random
import subprocess
import sys

import pytest

from braga_era.db import connect_read_only, file_sha256
from braga_era.engine import (
    EngineConfig,
    commit_seeds,
    prepare,
    simulate_match,
    validate_match,
)
from braga_era.engine.coaches import SelectionError, eligible
from braga_era.engine.match import finishing_probability
from braga_era.engine.narration import NarrationCursor
from braga_era.engine.randomness import stream
from braga_era.engine.sandbox import next_narration, run
from braga_era.engine.validation import validate_plans
from braga_era.engine.world import MissingRoster, World


@pytest.fixture
def snapshot(accepted_path):
    return World(accepted_path).first_recorded_fixture()


def play(snapshot, seed="unit-engine-seed", config=None):
    config = config or EngineConfig()
    seeds = commit_seeds(snapshot, config, seed)
    plans = prepare(snapshot, config, seeds)
    return simulate_match(snapshot, plans, config, seeds)


def test_exact_repeatability_and_no_global_rng(snapshot):
    before = random.getstate()
    a = play(snapshot)
    b = play(snapshot)
    assert a == b and a.fingerprint == b.fingerprint
    assert random.getstate() == before
    assert validate_match(snapshot, a).ok
    with pytest.raises(FrozenInstanceError):
        snapshot.kickoff = "2028-01-01"


def test_named_streams_do_not_interfere(snapshot):
    cfg = EngineConfig()
    seed = commit_seeds(snapshot, cfg, "streams")
    expected = stream(seed, "finishing").random()
    for _ in range(100):
        stream(seed, "other-purpose").random()
    assert stream(seed, "finishing").random() == expected


@pytest.mark.parametrize("change", ["snapshot", "config", "commitment"])
def test_seed_bound_to_inputs(snapshot, change):
    cfg = EngineConfig()
    seeds = commit_seeds(snapshot, cfg, "committed")
    plans = prepare(snapshot, cfg, seeds)
    if change == "snapshot":
        snapshot = replace(snapshot, kickoff="2027-10-04 16:00")
    if change == "config":
        cfg = replace(cfg, home_base_xg=1.7)
    if change == "commitment":
        seeds = replace(seeds, requested_seed="secret-reroll")
    with pytest.raises(ValueError):
        simulate_match(snapshot, plans, cfg, seeds)


def test_distribution_is_not_a_fixed_score(snapshot):
    results = [play(snapshot, f"distribution-{i}") for i in range(60)]
    assert len({r.score for r in results}) >= 8
    assert len({r.fingerprint for r in results}) == 60
    assert any(r.score[0] > r.score[1] for r in results)
    assert any(r.score[0] < r.score[1] for r in results)
    assert any(r.score[0] == r.score[1] for r in results)
    assert all(validate_match(snapshot, r).ok for r in results)


def test_vasco_has_no_guaranteed_win(accepted_path):
    s = World(accepted_path).synthetic()
    results = [play(s, f"vasco-distribution-{i}") for i in range(30)]
    assert any(r.score[0] < r.score[1] for r in results)
    assert any(r.score[0] > r.score[1] for r in results)


def test_exact_xi_eligibility_and_archived_identity(accepted_path):
    s = World(accepted_path).synthetic()
    r = play(s)
    assert s.home.coach.formation == "4-2-3-1 asymmetric"
    assert s.home.coach.defensive_shape == "4-4-2 midblock"
    for team, plan in zip((s.home, s.away), r.plans):
        lookup = {p.id: p for p in team.players}
        assert len(set(plan.starters)) == 11
        assert not set(plan.starters) & set(plan.bench)
        assert all(eligible(lookup[p], s) for p in plan.starters + plan.bench)
        assert 196 not in plan.starters + plan.bench
    assert any(p.id == 196 and not p.eligible for p in s.away.players)
    assert any(p.id == 354 and p.eligible for p in s.away.players)


@pytest.mark.parametrize("reason", ["injured", "suspended", "archived"])
def test_ineligible_high_rated_player_cannot_be_selected(snapshot, reason):
    r = play(snapshot)
    pid = r.plans[0].starters[-1]
    players = tuple(
        (
            replace(p, ovr=100, eligible=False, exclusion_reasons=(reason,))
            if p.id == pid
            else p
        )
        for p in snapshot.home.players
    )
    s = replace(snapshot, home=replace(snapshot.home, players=players))
    out = play(s)
    assert pid not in out.plans[0].starters + out.plans[0].bench
    assert validate_match(s, out).ok


def test_not_enough_players_fails_closed(snapshot):
    s = replace(
        snapshot, home=replace(snapshot.home, players=snapshot.home.players[:10])
    )
    with pytest.raises(SelectionError):
        play(s)


def test_no_eligible_goalkeeper_fails_closed(snapshot):
    s = replace(
        snapshot,
        home=replace(
            snapshot.home,
            players=tuple(
                replace(p, eligible=False) if p.position == "GK" else p
                for p in snapshot.home.players
            ),
        ),
    )
    with pytest.raises(SelectionError):
        play(s)


def test_coach_responds_to_current_form_and_fitness(snapshot):
    # Remove decision noise and give two candidates identical attributes except current form.
    team = snapshot.home
    fw = [p for p in team.players if p.position == "FW" and p.eligible]
    assert len(fw) >= 4
    best = fw[-1]
    updated = tuple(
        (
            replace(p, ovr=72, fitness=90, form=9.0 if p.id == best.id else 5.5)
            if p.position == "FW"
            else p
        )
        for p in team.players
    )
    s = replace(
        snapshot,
        home=replace(
            team, players=updated, coach=replace(team.coach, decision_noise=0)
        ),
    )
    assert best.id in play(s).plans[0].starters


def test_goalkeeper_finishing_and_form_have_symmetric_effect(snapshot):
    shooter = next(p for p in snapshot.home.players if p.position == "FW")
    keeper = next(p for p in snapshot.away.players if p.position == "GK")
    cfg = EngineConfig()
    weak = finishing_probability(0.15, shooter, replace(keeper, goalkeeping=50), cfg)
    strong = finishing_probability(0.15, shooter, replace(keeper, goalkeeping=95), cfg)
    assert 0 < strong < weak < 1
    assert finishing_probability(
        0.15, replace(shooter, form=8), keeper, cfg
    ) > finishing_probability(0.15, replace(shooter, form=5), keeper, cfg)


def test_identity_names_cannot_change_result(snapshot):
    r = play(snapshot)
    # Keep the actual plans, traits, attributes and root RNG streams; only display names differ.
    s = replace(snapshot, home=replace(snapshot.home, name="Vasco"))
    cfg = EngineConfig()
    seeds = commit_seeds(s, cfg, "unit-engine-seed")
    # A renamed input changes commitment by design; finishing functions have no team/name argument.
    assert seeds.snapshot_sha256 != r.snapshot_sha256
    from braga_era.engine.match import prematch

    assert prematch(snapshot, r.plans, cfg) == prematch(s, r.plans, cfg)


@pytest.mark.parametrize("seed", [f"event-accounting-{i}" for i in range(12)])
def test_full_event_and_player_accounting(snapshot, seed):
    r = play(snapshot, seed)
    v = validate_match(snapshot, r)
    assert v.ok, v.errors
    for team, score in zip((snapshot.home, snapshot.away), r.score):
        shots = [s for s in r.shots if s.club_key == team.key]
        perf = [p for p in r.performances if p.club_key == team.key]
        assert score == sum(s.goal for s in shots) == sum(p.goals for p in perf)
        assert len(shots) == sum(p.shots for p in perf)
        assert abs(sum(s.xg for s in shots) - sum(p.xg for p in perf)) < 0.0001
    assert all(p.fitness_after <= p.fitness_before for p in r.performances)
    assert all(p.form_after > 0 for p in r.performances)
    assert any(e.kind == "SUBSTITUTION" for e in r.events)


def test_forced_injury_and_red_cards_are_coherent(snapshot):
    cfg = replace(
        EngineConfig(),
        straight_red_probability_per_team=1,
        injury_probability_per_match=1,
        yellow_lambda=20,
    )
    for i in range(15):
        r = play(snapshot, f"forced-discipline-{i}", cfg)
        v = validate_match(snapshot, r, cfg)
        assert v.ok, v.errors
        assert sum(p.red for p in r.performances) >= 2
        assert sum(p.injured for p in r.performances) == 1
        for key in (snapshot.home.key, snapshot.away.key):
            assert (
                len(
                    {
                        e.elapsed_seconds
                        for e in r.events
                        if e.kind == "SUBSTITUTION" and e.club_key == key
                    }
                )
                <= 3
            )
        for e in r.events:
            if e.kind in ("RED_CARD", "INJURY"):
                assert not any(
                    later.player_id == e.player_id
                    and later.kind in ("GOAL", "SHOT", "SAVE", "YELLOW_CARD")
                    for later in r.events[e.sequence :]
                )


def test_second_yellow_removes_player(snapshot):
    cfg = replace(EngineConfig(), yellow_lambda=20, straight_red_probability_per_team=0)
    results = [play(snapshot, f"second-yellow-{i}", cfg) for i in range(25)]
    assert any(
        e.kind == "RED_CARD" and e.details["reason"] == "second yellow"
        for r in results
        for e in r.events
    )
    assert all(validate_match(snapshot, r, cfg).ok for r in results)


def test_same_clock_substitution_precedes_shot(snapshot, monkeypatch):
    # A deterministic stub deliberately collides a coach window and all shots at minute 59.
    from braga_era.engine import match

    original = match.stream

    class Collision:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def randint(self, a, b):
            return 59 * 60

    monkeypatch.setattr(
        match,
        "stream",
        lambda seeds, purpose: (
            Collision(original(seeds, purpose))
            if purpose == "chance-generation"
            else original(seeds, purpose)
        ),
    )
    cfg = EngineConfig()
    seeds = commit_seeds(snapshot, cfg, "same-clock")
    plans = tuple(
        replace(p, substitution_minutes=(59, 73, 82))
        for p in prepare(snapshot, cfg, seeds)
    )
    r = simulate_match(snapshot, plans, cfg, seeds)
    collisions = [e for e in r.events if e.elapsed_seconds == 59 * 60]
    assert collisions[0].kind in ("SUBSTITUTION", "TACTICAL_CHANGE")
    assert max(e.sequence for e in collisions if e.kind == "SUBSTITUTION") < min(
        e.sequence for e in collisions if e.kind == "SHOT"
    )
    assert validate_match(snapshot, r).ok


@pytest.mark.parametrize(
    "tamper",
    [
        "score",
        "sequence",
        "actor",
        "assist",
        "participation",
        "club",
        "period",
        "xg",
        "clock",
        "fixture",
    ],
)
def test_auditor_rejects_tampered_reports(snapshot, tamper):
    r = play(snapshot, "tamper-has-goals")
    if tamper == "score":
        r = replace(r, score=(99, 99))
    elif tamper == "sequence":
        r = replace(r, events=(replace(r.events[0], sequence=100),) + r.events[1:])
    elif tamper in ("actor", "assist", "period", "clock"):
        events = list(r.events)
        index = next(
            i
            for i, e in enumerate(events)
            if e.kind == ("GOAL" if tamper == "assist" else "SHOT")
        )
        e = events[index]
        if tamper == "actor":
            e = replace(e, player_id=196)
        if tamper == "assist":
            e = replace(e, details={**e.details, "assist_id": 196})
        if tamper == "period":
            e = replace(e, period="ET")
        if tamper == "clock":
            e = replace(e, elapsed_seconds=-1)
        events[index] = e
        r = replace(r, events=tuple(events))
    elif tamper == "participation":
        r = replace(
            r,
            performances=(replace(r.performances[0], seconds_played=99999),)
            + r.performances[1:],
        )
    elif tamper == "club":
        r = replace(
            r,
            performances=(replace(r.performances[0], club_key="unknown"),)
            + r.performances[1:],
        )
    elif tamper == "xg":
        r = replace(r, shots=(replace(r.shots[0], xg=9),) + r.shots[1:])
    elif tamper == "fixture":
        r = replace(r, fixture_key="other")
    assert not validate_match(snapshot, r).ok


def test_illegal_plan_rejected(snapshot):
    r = play(snapshot)
    plan = r.plans[0]
    plans = (replace(plan, bench=plan.bench + plan.starters[:1]), r.plans[1])
    assert validate_plans(snapshot, plans)
    with pytest.raises(ValueError):
        simulate_match(snapshot, plans, EngineConfig(), r.seeds)


@pytest.mark.parametrize(
    "field,value",
    [
        ("chance_beta_a", 0),
        ("injury_probability_per_match", 2),
        ("yellow_lambda", float("nan")),
        ("shot_count_lambda", 1000),
        ("maximum_substitutions", 6),
        ("isolated_rng_streams", False),
    ],
)
def test_invalid_configuration_rejected(snapshot, field, value):
    with pytest.raises(ValueError):
        play(snapshot, config=replace(EngineConfig(), **{field: value}))


def test_official_scope_and_unimplemented_competition_resolution_fail_closed(snapshot):
    with pytest.raises(ValueError, match="noncanonical"):
        play(replace(snapshot, scope="OFFICIAL"))
    with pytest.raises(NotImplementedError):
        play(replace(snapshot, rules=replace(snapshot.rules, extra_time_if_tied=True)))


def test_settled_fixture_and_missing_foreign_rosters_fail_closed(accepted_path):
    w = World(accepted_path)
    with pytest.raises(ValueError, match="Settled"):
        w.load_pregame("league:322")
    with connect_read_only(accepted_path) as c:
        rows = list(
            c.execute(
                "SELECT event_id FROM calendar_events WHERE kickoff LIKE '2027-09-30%' AND status='scheduled'"
            )
        )
    assert rows
    for row in rows:
        with pytest.raises(MissingRoster):
            w.load_pregame("calendar:" + row[0])


def test_input_snapshots_do_not_write_database(accepted_path, canonical_path):
    before = [file_sha256(p) for p in (accepted_path, canonical_path)]
    s = World(accepted_path).synthetic()
    play(s)
    assert before == [file_sha256(p) for p in (accepted_path, canonical_path)]


def test_global_agenda_orders_continental_before_r26():
    from braga_era.engine.competitions import CalendarEntry, ordered_agenda

    league = CalendarEntry(
        "league:vasco-r26", "2027-10-03 16:00", "Brasileirão", 2027, True
    )
    continental = CalendarEntry(
        "libertadores:leg1", "2027-09-30 21:30", "Libertadores", 2027, True
    )
    assert ordered_agenda((league, continental)) == (continental, league)
    with pytest.raises(ValueError):
        ordered_agenda((league, league))


def test_narration_withholds_future_results(snapshot):
    r = play(snapshot)
    cursor = NarrationCursor(snapshot, r)
    initial = cursor.preview()
    assert "score" not in initial and "performances" not in initial
    assert not initial["postmatch_available"]
    seen = []
    while True:
        batch = cursor.next()
        seen.extend(batch["events"])
        if batch["postmatch_available"]:
            assert seen[-1]["kind"] == "FINAL_WHISTLE"
            assert batch["postmatch_summary"]["score"] == list(r.score)
            break
        assert "postmatch_summary" not in batch
        for e in batch["events"]:
            if e["kind"] == "SHOT":
                assert (
                    not {"goal", "on_target", "goal_probability"} & e["details"].keys()
                )
    assert [e["sequence"] for e in seen] == list(range(1, len(r.events) + 1))


def test_sandbox_copy_report_and_persistent_cursor(accepted_path, tmp_path):
    before = file_sha256(accepted_path)
    out = tmp_path / "sandbox"
    receipt = run(accepted_path, out, "integration-sandbox", synthetic=True)
    assert receipt["synthetic"] and not receipt["official_records_changed"]
    assert "score" not in receipt
    report = json.loads((out / "private_match_report.json").read_text(encoding="utf-8"))
    assert (
        report["validation"]["ok"] and report["scope"] == "NONCANONICAL TEST SIMULATION"
    )
    assert file_sha256(out / "scratch.sqlite") == file_sha256(accepted_path) == before
    assert (
        json.loads((out / "seed_commitment.json").read_text())
        == report["result"]["seeds"]
    )
    first = next_narration(out)
    second = next_narration(out)
    assert first["events"][0]["sequence"] == 1 and second["events"][0]["sequence"] == 2
    assert "postmatch_summary" not in first
    while not second["postmatch_available"]:
        second = next_narration(out, 20)
    assert "postmatch_summary" in second
    with pytest.raises(FileExistsError):
        run(accepted_path, out, "integration-sandbox")


def test_cursor_rejects_changed_result(accepted_path, tmp_path):
    out = tmp_path / "sandbox"
    run(accepted_path, out, "cursor-integrity")
    file = out / "private_match_report.json"
    report = json.loads(file.read_text(encoding="utf-8"))
    report["result"]["score"] = [99, 99]
    file.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        next_narration(out)
    assert not (out / "narration.lock").exists()


def test_cursor_rejects_changed_summary(accepted_path, tmp_path):
    out = tmp_path / "summary-integrity"
    run(accepted_path, out, "summary-integrity")
    path = out / "private_match_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["sealed_postmatch_summary"]["score"] = [99, 99]
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="summary changed"):
        next_narration(out)


def test_sandbox_and_narration_cli_outside_repository(accepted_path, tmp_path):
    out = tmp_path / "cli-demo"
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "braga_era",
            "sandbox",
            "--db",
            str(accepted_path.resolve()),
            "--output",
            str(out),
            "--seed",
            "cli-seed",
            "--synthetic",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["validation_passed"]
    done = subprocess.run(
        [sys.executable, "-m", "braga_era", "narrate", str(out)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["events"][0]["kind"] == "KICKOFF"
    assert "postmatch_summary" not in json.loads(done.stdout)
