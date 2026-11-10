"""Deterministic fixtures for the forward-only substitution policy."""

from collections import Counter
from dataclasses import asdict, replace
from random import Random

import pytest

from braga_era.engine import commit_seeds, prepare, simulate_match, validate_match
from braga_era.engine import match
from braga_era.engine.models import CompetitionRules, Player, Snapshot, Team
from braga_era.engine.substitutions import TACTICAL_REASON, VERSION, choose_tactical
from braga_era.history import digest
from braga_era.world.forward_config import configuration, load
from braga_era.world import knockout_v2
from braga_era.world.knockout_v2 import resolve, validate_bundle
from braga_era.world.policy import ReadinessPolicy, Rules


def fixture():
    def team(key, offset):
        positions = ("GK", "DF", "DF", "DF", "DF", "MF", "MF", "MF", "FW", "FW", "FW",
                     "GK", "FW", "FW", "FW", "MF", "DF")
        return Team(key, key, 73, 0, tuple(
            Player(offset + i, key, f"{key} {i}", pos,
                   {9: 60, 13: 85, 14: 82, 15: 79}.get(i, 74),
                   73, 73, 73, 73, 73, 80 if pos == "GK" else 25,
                   {9: 70, 13: 72, 14: 75, 15: 78}.get(i, 98), 50)
            for i, pos in enumerate(positions, 1)
        ))
    return Snapshot("dev:substitution-policy", "2028-01-10 16:00", "2028-01-10 00:00",
                    team("Home", 0), team("Away", 100), CompetitionRules("STATE", 2028), "0"*64)


def config(forward=True, **overrides):
    return replace(configuration(ReadinessPolicy(), engine_version=VERSION if forward else None), **overrides)


def play(snapshot, cfg, seed, *, fixed_plans=False):
    seeds = commit_seeds(snapshot, cfg, seed)
    plans = prepare(snapshot, cfg, seeds)
    if fixed_plans:
        slots = ("GK", "RB", "CB1", "CB2", "LB", "DM", "CM1", "CM2", "RW", "LW", "ST")
        plans = tuple(replace(p, starters=tuple(q.id for q in t.players[:11]),
                              bench=tuple(q.id for q in t.players[11:] if q.eligible),
                              roles=tuple((q.id, slot) for q, slot in zip(t.players, slots)),
                              substitution_minutes=(62, 76, 84))
                      for p, t in zip(plans, (snapshot.home, snapshot.away)))
    return simulate_match(snapshot, plans, cfg, seeds)


def substitutions(result, club="Home"):
    return [(e.elapsed_seconds // 60, e.details["outgoing_id"], e.player_id)
            for e in result.events if e.kind == "SUBSTITUTION" and e.club_key == club]


def test_old_chain_is_reproduced_and_new_policy_spares_every_substitute():
    snapshot = fixture()
    overrides = dict(yellow_lambda=0, injury_probability_per_match=0, straight_red_probability_per_team=0)
    old = play(snapshot, config(False, **overrides), "chain-3", fixed_plans=True)
    assert substitutions(old) == [(62, 9, 13), (76, 13, 14), (84, 14, 15)]
    cfg = config(**overrides)
    new = play(snapshot, cfg, "chain-3", fixed_plans=True)
    assert substitutions(new)[0] == (62, 9, 13)
    assert all(old_id <= 11 for _, old_id, _ in substitutions(new))
    assert next(p.seconds_played for p in new.performances if p.player_id == 13) == (93 - 62) * 60
    assert validate_match(snapshot, new, cfg).ok
    assert new == play(snapshot, cfg, "chain-3", fixed_plans=True)


@pytest.mark.parametrize(("difference", "chosen"), [(-1, 11), (0, 7), (1, 3)])
def test_score_context_and_repeat_penalty(difference, chosen):
    pool = {p.id: replace(p, ovr=74, fitness=95) for p in fixture().home.players}
    active = {3: 70 * 60, 7: 70 * 60, 11: 70 * 60}
    stats = {p: dict(starter=True, injured=False, red=False, goals=0, assists=0, yellows=0) for p in active}
    roles = {3: "CB1", 7: "CM1", 11: "ST"}
    args = (pool, {15, 16, 17}, roles, active, stats, difference)
    first = choose_tactical(*args, {}, Random(1), 0)
    assert first[0] == chosen
    repeated = choose_tactical(*args, {pool[chosen].position: 1}, Random(1), 0)
    assert repeated and repeated[0] != chosen
    assert choose_tactical(pool, {12}, roles, active, stats, difference, {}, Random(1), 0) is None
    assert choose_tactical(pool, {15, 16, 17}, roles, dict.fromkeys(active, 60), stats,
                           difference, {}, Random(1), 2) is None
    stats[chosen]["goals"] = 2
    assert choose_tactical(*args, {}, Random(1), 0)[0] != chosen


def test_ineligible_outfield_bench_produces_no_tactical_changes():
    snapshot = fixture()
    home = replace(snapshot.home, players=tuple(
        replace(p, eligible=False, exclusion_reasons=("suspended",)) if p.id >= 13 else p
        for p in snapshot.home.players
    ))
    snapshot = replace(snapshot, home=home)
    cfg = config(straight_red_probability_per_team=0, injury_probability_per_match=0)
    result = play(snapshot, cfg, "short-bench")
    assert len(result.plans[0].bench) == 1 and result.plans[0].bench[0] in (1, 12)
    assert substitutions(result) == []
    assert validate_match(snapshot, result, cfg).ok


def test_eligible_reserve_keeper_is_kept_on_a_deep_bench():
    snapshot = fixture()
    players = tuple(replace(p, ovr=55) if p.id == 12 else p for p in snapshot.home.players)
    players += tuple(replace(players[3], id=200 + i) for i in range(18))
    snapshot = replace(snapshot, home=replace(snapshot.home, players=players))
    cfg = config()
    plans = prepare(snapshot, cfg, commit_seeds(snapshot, cfg, "deep-bench"))
    assert len(plans[0].bench) == 12 and 12 in plans[0].bench


@pytest.mark.parametrize("minute", [62, 63])
def test_injured_new_substitute_can_be_replaced(monkeypatch, minute):
    class Injury:
        def random(self): return 0
        def randint(self, *_): return minute * 60
        def randrange(self, *_): return 0
        def choice(self, ids):
            assert 13 in ids
            return 13

    original = match.stream
    monkeypatch.setattr(match, "stream", lambda seed, name: Injury() if name == "injuries" else original(seed, name))
    snapshot = fixture()
    cfg = config(straight_red_probability_per_team=0, yellow_lambda=0)
    result = play(snapshot, cfg, "injury-0", fixed_plans=True)
    assert substitutions(result)[:2] == [(62, 9, 13), (minute, 13, 14)]
    event = next(e for e in result.events if e.kind == "SUBSTITUTION" and e.details["outgoing_id"] == 13)
    assert event.details["reason"] == "injury replacement"
    appearance = next(p for p in result.performances if p.player_id == 13)
    assert appearance.seconds_played == (minute - 62) * 60 and appearance.injured
    assert validate_match(snapshot, result, cfg).ok


@pytest.mark.parametrize("allowance", [0, 2])
def test_goalkeeper_red_card_preserves_short_handed_count(monkeypatch, allowance):
    class Dismissal:
        def random(self): return 0
        def randint(self, *_): return 65 * 60
        def choices(self, ids, **_): return [min(ids)]

    original = match.stream
    monkeypatch.setattr(match, "stream", lambda seed, name: Dismissal() if name == "discipline" else original(seed, name))
    snapshot = fixture()
    cfg = config(maximum_substitutions=allowance, yellow_lambda=0, injury_probability_per_match=0)
    result = play(snapshot, cfg, "dismissal", fixed_plans=True)
    red = next(e for e in result.events if e.kind == "RED_CARD" and e.club_key == "Home")
    emergency = result.events[red.sequence]
    assert emergency.elapsed_seconds == red.elapsed_seconds
    assert len(emergency.on_field_home) == len(red.on_field_home) == 10
    assert emergency.kind == ("SUBSTITUTION" if allowance else "EMERGENCY_GOALKEEPER")
    if allowance:
        assert emergency.player_id == 12
    else:
        assert emergency.player_id in red.on_field_home
    assert 1 not in result.events[-1].on_field_home
    assert validate_match(snapshot, result, cfg).ok


def test_window_limit_stops_tactical_replacements_even_with_quota_left():
    snapshot = fixture()
    cfg = config(maximum_substitution_windows=1, yellow_lambda=0,
                 injury_probability_per_match=0, straight_red_probability_per_team=0)
    result = play(snapshot, cfg, "windows", fixed_plans=True)
    assert [len(substitutions(result, team)) for team in ("Home", "Away")] == [1, 1]
    assert validate_match(snapshot, result, cfg).ok


def test_extra_time_has_one_more_replacement_and_free_intervals():
    snapshot = fixture()
    cfg = config(maximum_substitutions=1, maximum_substitution_windows=1, yellow_lambda=0,
                 injury_probability_per_match=0, straight_red_probability_per_team=0)
    result = play(snapshot, cfg, "extra", fixed_plans=True)
    rules = Rules("STATE", extra_time=True, penalties=True)
    prior = result.score[::-1]
    bundle = resolve(snapshot, result, cfg, rules, prior)
    assert validate_bundle(snapshot, result, cfg, rules, prior, bundle)["independent_extension_accounting"]
    assert bundle == resolve(snapshot, result, cfg, rules, prior)
    for plan in result.plans:
        events = [e for e in bundle["events"] if e["kind"] == "SUBSTITUTION" and e["club_key"] == plan.club_key]
        assert len(events) == 2
        assert events[-1]["details"]["interval"]
        assert events[-1]["details"]["outgoing_id"] in plan.starters
    assert bundle["duration_seconds"] >= result.duration_seconds + 1800


def test_extra_time_goalkeeper_dismissal_and_emergency_window(monkeypatch):
    snapshot = fixture()
    cfg = config(yellow_lambda=0, injury_probability_per_match=0)
    result = play(snapshot, cfg, "extra", fixed_plans=True)
    assert not any(e.kind == "RED_CARD" for e in result.events)
    keepers = {p.id for team in (snapshot.home, snapshot.away) for p in team.players if p.position == "GK"}

    class Forced(Random):
        def random(self): return 0
        def choice(self, ids): return next(p for p in ids if p in keepers)

    original = knockout_v2.stream
    monkeypatch.setattr(knockout_v2, "stream", lambda seed, name:
                        Forced(7) if name.endswith(":extra-time") else original(seed, name))
    rules = Rules("STATE", extra_time=True, penalties=True)
    prior = result.score[::-1]
    bundle = resolve(snapshot, result, cfg, rules, prior)
    assert validate_bundle(snapshot, result, cfg, rules, prior, bundle)["ok"]
    for field in ("on_field_home", "on_field_away"):
        key = "Home" if field == "on_field_home" else "Away"
        red = next(e for e in bundle["events"] if e["kind"] == "RED_CARD" and e["club_key"] == key)
        emergency = bundle["events"][red["sequence"]]
        assert len(red[field]) == len(emergency[field]) == 10
        assert emergency["details"]["reason"] == "emergency goalkeeper replacement"
        assert emergency["details"]["interval"] is False
        assert emergency["player_id"] in keepers and red["player_id"] not in emergency[field]


def test_registered_configs_keep_legacy_and_neutral_versions_exact():
    policy = ReadinessPolicy()
    with pytest.raises(ValueError, match="Unsupported"):
        load([], policy)
    for neutral in (False, True):
        legacy = configuration(policy, neutral)
        modern = configuration(policy, neutral, engine_version=VERSION)
        assert legacy.version == "braga-headless-1.1.0"
        assert load(asdict(legacy), policy, neutral) == legacy
        assert load(asdict(modern), policy, neutral) == modern
        assert legacy.fingerprint != modern.fingerprint
        with pytest.raises(ValueError, match="Unsupported"):
            load({**asdict(modern), "lineup_fitness_weight": 1}, policy, neutral)


def test_frozen_installed_legacy_regulation_extra_time_and_shootouts():
    snapshot = fixture()
    bundles = []
    for i in range(40):
        cfg = configuration(ReadinessPolicy(), final=(i % 2 == 0))
        result = play(snapshot, cfg, f"frozen-legacy-{i}")
        rules = Rules("STATE", extra_time=True, penalties=True)
        bundles.append(resolve(snapshot, result, cfg, rules, result.score[::-1]))
    assert digest(bundles) == "48e710674c8865dcf314ea72aa329d818c75de83b5c6698b1d286a313e22279d"


def comparison():
    """Fixed 300 paired varied fixtures, including 60 forced aggregate ties."""
    totals = {}
    for forward in (False, True):
        counts = Counter()
        cfg = config(forward)
        for i in range(300):
            snapshot = fixture()
            rng = Random(i)
            def vary(team):
                return replace(team, strength=rng.randint(65, 85), players=tuple(
                    replace(p, ovr=rng.randint(64, 85), fitness=rng.randint(70, 100),
                            form=5.5 + rng.random()*2.5, eligible=p.id % 100 <= 11 or rng.random() > 0.15)
                    for p in team.players))
            snapshot = replace(snapshot, home=vary(snapshot.home), away=vary(snapshot.away))
            result = play(snapshot, cfg, f"paired-substitution-{i}")
            assert validate_match(snapshot, result, cfg).ok
            events = [asdict(e) for e in result.events]
            if i % 5 == 0:
                prior = result.score[::-1]
                rules = Rules("STATE", extra_time=True, penalties=True)
                bundle = resolve(snapshot, result, cfg, rules, prior)
                assert validate_bundle(snapshot, result, cfg, rules, prior, bundle)["ok"]
                events = bundle["events"]
            subs = set()
            for event in events:
                if event["kind"] != "SUBSTITUTION":
                    continue
                counts["changes"] += 1
                if event["details"]["outgoing_id"] in subs:
                    medical = event["details"]["reason"] == "injury replacement" or any(
                        e["kind"] == "INJURY" and e["elapsed_seconds"] == event["elapsed_seconds"]
                        and e["player_id"] == event["details"]["outgoing_id"] for e in events)
                    keeper = "goalkeeper" in event["details"]["reason"]
                    counts["emergency_chains" if medical or keeper else "tactical_chains"] += 1
                subs.add(event["player_id"])
        totals[cfg.version] = counts
    return totals


def test_varied_match_corpus():
    totals = comparison()
    assert totals["braga-headless-1.1.0"]["tactical_chains"] > 0
    assert totals[VERSION]["tactical_chains"] == 0
    assert totals[VERSION]["changes"] > 300
