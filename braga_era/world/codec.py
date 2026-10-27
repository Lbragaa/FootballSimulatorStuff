"""Explicit JSON decoding for engine contracts; no pickle or archive code execution."""

from ..engine.models import (
    Player,
    Coach,
    Team,
    Snapshot,
    CompetitionRules,
    MatchPlan,
    MatchResult,
    SeedCommitment,
    Prematch,
    Event,
    Shot,
    Performance,
)


def player(data):
    d = dict(data)
    d["exclusion_reasons"] = tuple(d["exclusion_reasons"])
    d["recent_ratings"] = tuple(tuple(r) for r in d["recent_ratings"])
    return Player(**d)


def snapshot(data):
    d = dict(data)
    for side in ("home", "away"):
        t = dict(d[side])
        t["players"] = tuple(player(p) for p in t["players"])
        t["coach"] = Coach(**t["coach"])
        d[side] = Team(**t)
    r = dict(d["rules"])
    if r["aggregate_before"] is not None:
        r["aggregate_before"] = tuple(r["aggregate_before"])
    d["rules"] = CompetitionRules(**r)
    d["archived_ids"] = tuple(d["archived_ids"])
    d["notes"] = tuple(d["notes"])
    return Snapshot(**d)


def result(data):
    d = dict(data)
    plans = []
    for p in d["plans"]:
        p = dict(p)
        for k in ("starters", "bench", "substitution_minutes", "rationale"):
            p[k] = tuple(p[k])
        p["roles"] = tuple(tuple(r) for r in p["roles"])
        plans.append(MatchPlan(**p))
    d["plans"] = tuple(plans)
    d["seeds"] = SeedCommitment(**d["seeds"])
    p = dict(d["prematch"])
    p["expected_xg"] = tuple(p["expected_xg"])
    d["prematch"] = Prematch(**p)
    events = []
    for e in d["events"]:
        e = dict(e)
        for k in ("pre_score", "post_score", "on_field_home", "on_field_away"):
            e[k] = tuple(e[k])
        events.append(Event(**e))
    d["events"] = tuple(events)
    d["shots"] = tuple(Shot(**s) for s in d["shots"])
    d["performances"] = tuple(Performance(**p) for p in d["performances"])
    d["score"] = tuple(d["score"])
    return MatchResult(**d)
