"""One-time committed execution, simultaneous snapshots and transactional group application."""

from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from ..engine import EngineConfig, commit_seeds, prepare, simulate_match
from ..engine.match import prematch
from ..engine.narration import preview as engine_preview
from ..engine.models import SeedCommitment
from ..history import canonical_json as encode, digest
from ..payroll import obligations, book_payroll, POLICY_ID
from ..state import ACCOUNT
from . import SCOPE
from . import codec
from .storage import writer, transaction, logical_hash
from .adapters import adapter
from .knockout import resolve, validate_bundle
from .players import apply_players, moment, stamp
from .audit import audit
from .policy import is_readiness, ReadinessPolicy
from .forward_config import configuration, load as load_config
from .forward_schema import enabled as forward_enabled


def resolution_functions(policy):
    if is_readiness(policy):
        if policy.extension_version == "braga-knockout-2.0.0":
            from .knockout_v2_0 import (
                resolve as forward_resolve,
                validate_bundle as forward_validate,
            )
        else:
            from .knockout_v2 import (
                resolve as forward_resolve,
                validate_bundle as forward_validate,
            )
        return forward_resolve, forward_validate
    return resolve, validate_bundle


class InjectedCrash(RuntimeError):
    pass


def fault(requested, stage):
    if requested == stage:
        raise InjectedCrash("Injected crash: " + stage)


def context(c, f, policy, world_hash):
    a = adapter(c, f["competition"], policy)
    snapshot = a.pregame(f["key"], world_hash)
    rules = a.rules_for(f["key"])
    prior = (0, 0)
    if f["tie_key"]:
        tie = c.execute(
            "SELECT * FROM world_ties WHERE key=?", (f["tie_key"],)
        ).fetchone()
        prior = (
            (tie["aggregate_a"], tie["aggregate_b"])
            if tie["club_a"] == f["home"]
            else (tie["aggregate_b"], tie["aggregate_a"])
        )
    return snapshot, rules, prior


def make_preview(snapshot, plans, config, seeds):
    value = engine_preview(
        snapshot,
        SimpleNamespace(plans=plans, prematch=prematch(snapshot, plans, config)),
    )
    value.update(scope=SCOPE, seed_commitment=asdict(seeds), official=False)
    return value


def pending(c):
    return c.execute(
        "SELECT * FROM world_batches WHERE status<>'applied' ORDER BY kickoff,key LIMIT 1"
    ).fetchone()


def agenda(c):
    fixtures = [
        dict(r, kind="match")
        for r in c.execute(
            "SELECT * FROM world_fixtures f WHERE status<>'final' AND NOT EXISTS(SELECT 1 FROM world_executions e WHERE e.fixture_key=f.key)"
        )
    ]
    admin = [
        dict(r, kind="administrative")
        for r in c.execute("SELECT * FROM world_obligations WHERE status='scheduled'")
    ]
    finishes = [
        dict(r, kind="completion", kickoff=r["finish_time"])
        for r in c.execute("SELECT * FROM world_batches WHERE status='simulated'")
    ]
    from .forward_schema import enabled

    if enabled(c):
        from .progression import reservation_draw

        fixtures = [
            f
            for f in fixtures
            if ":reserve:" not in f["key"] or not reservation_draw(c, f["key"])
        ]
    return sorted(
        fixtures + admin + finishes,
        key=lambda r: (
            moment(r["kickoff"]),
            {"completion": 0, "administrative": 1, "match": 2}[r["kind"]],
            r["key"],
        ),
    )


def claim(c, fixtures, policy):
    kickoff = fixtures[0]["kickoff"]
    batch_key = "batch:" + kickoff
    if c.execute("SELECT 1 FROM world_batches WHERE status='claimed'").fetchone():
        raise ValueError("Resume the earlier claim before allocating any new execution")
    clubs = [f[k] for f in fixtures for k in ("home", "away")]
    if None in clubs:
        raise ValueError("Unresolved qualifier/draw at " + kickoff)
    if len(set(clubs)) != len(clubs):
        raise ValueError("A club has overlapping simultaneous fixtures")
    ongoing = {
        r[k]
        for r in c.execute(
            "SELECT f.* FROM world_fixtures f JOIN world_executions e ON e.fixture_key=f.key WHERE e.status<>'applied'"
        )
        for k in ("home", "away")
    }
    if ongoing.intersection(clubs):
        raise ValueError("Club already has an unfinished overlapping fixture")
    if moment(kickoff) < moment(
        c.execute("SELECT clock FROM world_info").fetchone()[0]
    ):
        raise ValueError("Agenda would move backwards or overlap a previous match")
    world_hash = logical_hash(c)
    prepared = []
    root = c.execute("SELECT seed FROM world_info").fetchone()[0]
    for f in fixtures:
        config = configuration(policy, f["stage"] == "Final única")
        if (
            f["status"] != "scheduled"
            or c.execute(
                "SELECT 1 FROM world_executions WHERE fixture_key=?", (f["key"],)
            ).fetchone()
        ):
            raise ValueError("Already-final/claimed or conditional fixture")
        snapshot, rules, prior = context(c, f, policy, world_hash)
        seeds = commit_seeds(snapshot, config, root + ":" + f["key"])
        prepared.append((f, snapshot, rules, prior, seeds, config))
    # All inputs in this group are captured from precisely the same pre-kickoff world.
    with transaction(c, "claim:" + batch_key):
        c.execute(
            "INSERT INTO world_batches VALUES(?,?,?,?,?)",
            (batch_key, kickoff, "claimed", world_hash, None),
        )
        for f, snapshot, rules, prior, seeds, config in prepared:
            data = {
                "snapshot": asdict(snapshot),
                "rules": asdict(rules),
                "prior": list(prior),
            }
            c.execute(
                "INSERT INTO world_executions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f["key"],
                    batch_key,
                    "claimed",
                    encode(data),
                    digest(data),
                    encode(asdict(config)),
                    encode(asdict(seeds)),
                    None,
                    None,
                    None,
                    "{}",
                ),
            )
        c.execute("UPDATE world_info SET clock=?", (kickoff,))
    return batch_key


def simulate_pending(c, batch_key, policy, crash=None):
    from .policy import Rules

    for row in c.execute(
        "SELECT * FROM world_executions WHERE batch_key=? ORDER BY fixture_key",
        (batch_key,),
    ).fetchall():
        if row["status"] == "simulated":
            continue
        data = json.loads(row["input_json"])
        if digest(data) != row["input_sha256"]:
            raise ValueError("Committed snapshot changed")
        config = load_config(
            json.loads(row["config_json"]), policy, data["rules"]["extra_time"]
        )
        snapshot = codec.snapshot(data["snapshot"])
        seeds = SeedCommitment(**json.loads(row["seed_json"]))
        rules = Rules(**data["rules"])
        plans = prepare(snapshot, config, seeds)
        preview = make_preview(snapshot, plans, config, seeds)
        result = simulate_match(snapshot, plans, config, seeds)
        resolver, validator = resolution_functions(policy)
        bundle = resolver(snapshot, result, config, rules, tuple(data["prior"]))
        validation = validator(
            snapshot, result, config, rules, tuple(data["prior"]), bundle
        )
        with transaction(c, "result:" + row["fixture_key"]):
            c.execute(
                "UPDATE world_executions SET status='simulated',result_json=?,result_sha256=?,validation_json=?,preview_json=? WHERE fixture_key=? AND status='claimed'",
                (
                    encode(bundle),
                    digest(bundle),
                    encode(validation),
                    encode(preview),
                    row["fixture_key"],
                ),
            )
        fault(crash, "after_result")
    rows = c.execute(
        "SELECT e.result_json,f.kickoff FROM world_executions e JOIN world_fixtures f ON f.key=e.fixture_key WHERE batch_key=?",
        (batch_key,),
    ).fetchall()
    finish = max(
        stamp(
            moment(r["kickoff"])
            + timedelta(seconds=json.loads(r["result_json"])["duration_seconds"])
        )
        for r in rows
    )
    with transaction(c, "ready:" + batch_key):
        c.execute(
            "UPDATE world_batches SET status='simulated',finish_time=? WHERE key=?",
            (finish, batch_key),
        )


def apply_batch(c, batch_key, policy, parent, crash=None):
    rows = c.execute(
        "SELECT * FROM world_executions WHERE batch_key=? ORDER BY fixture_key",
        (batch_key,),
    ).fetchall()
    if not rows or any(r["status"] != "simulated" for r in rows):
        raise ValueError("Batch is incomplete; no partial application allowed")
    end = None
    with transaction(c, "apply:" + batch_key):
        for row in rows:
            bundle = json.loads(row["result_json"])
            if digest(bundle) != row["result_sha256"]:
                raise ValueError("Stored result changed; do not reroll")
            f = c.execute(
                "SELECT * FROM world_fixtures WHERE key=?", (row["fixture_key"],)
            ).fetchone()
            if (
                f["status"] != "scheduled"
                or c.execute(
                    "SELECT 1 FROM world_receipts WHERE fixture_key=?", (f["key"],)
                ).fetchone()
            ):
                raise ValueError("Duplicate or settled fixture application")
            data = json.loads(row["input_json"])
            snapshot = codec.snapshot(data["snapshot"])
            # Revalidate stored input/result, including all regulation accounting, on crash resumption.
            from .policy import Rules

            _, validator = resolution_functions(policy)
            validator(
                snapshot,
                codec.result(bundle["regulation"]),
                load_config(
                    json.loads(row["config_json"]), policy, f["stage"] == "Final única"
                ),
                Rules(**data["rules"]),
                tuple(data["prior"]),
                bundle,
            )
            finished = stamp(
                moment(f["kickoff"]) + timedelta(seconds=bundle["duration_seconds"])
            )
            end = max(end or finished, finished)
            c.execute(
                "INSERT INTO world_receipts VALUES(?,?,?)",
                (f["key"], row["result_sha256"], finished),
            )
            adapter(c, f["competition"], policy).apply(f, bundle)
            apply_players(c, f, snapshot, bundle, policy)
            for e in bundle["events"]:
                c.execute(
                    "INSERT INTO world_events VALUES(?,?,?)",
                    (f["key"], e["sequence"], encode(e)),
                )
            for p in bundle["performances"]:
                c.execute(
                    "INSERT INTO world_performances VALUES(?,?,?)",
                    (f["key"], p["player_id"], encode(p)),
                )
            c.execute(
                "UPDATE world_executions SET status='applied' WHERE fixture_key=?",
                (f["key"],),
            )
            fault(crash, "during_apply")
        c.execute("UPDATE world_batches SET status='applied' WHERE key=?", (batch_key,))
        c.execute("UPDATE world_info SET clock=?", (end,))
        audit(c, parent, check_journal=False, validate_results=not is_readiness(policy))
        fault(crash, "before_commit")


def apply_obligation(c, item, parent):
    period = item["key"].split(":")[1]
    with transaction(c, "obligation:" + item["key"]):
        entries = obligations(c, period, item["kickoff"])
        due = sum(r["due_cents"] for r in entries)
        registered = c.execute(
            "SELECT * FROM payroll_periods WHERE period=?", (period,)
        ).fetchone()
        if not registered:
            c.execute(
                "INSERT INTO payroll_periods VALUES(?,?,?,?,?,?,?,?)",
                (period, ACCOUNT, POLICY_ID, "accrued", due, due, 0, None),
            )
            for r in entries:
                c.execute(
                    "INSERT INTO payroll_obligations VALUES(?,?,?,?,?,?,?)",
                    tuple(
                        r[k]
                        for k in (
                            "period",
                            "player_id",
                            "covered_from",
                            "covered_to",
                            "monthly_cents",
                            "due_cents",
                            "accrued_cents",
                        )
                    ),
                )
        elif registered["amount_due_cents"] != due:
            raise ValueError(
                "Registered payroll differs from the accepted contract policy"
            )
        ledger, posted = book_payroll(c, period, due, item["kickoff"])
        c.execute(
            "UPDATE world_obligations SET status='paid',detail_json=? WHERE key=?",
            (
                encode(
                    {
                        "ledger_id": ledger,
                        "cash_cents": due,
                        "posted": posted,
                        "policy": POLICY_ID,
                    }
                ),
                item["key"],
            ),
        )
        c.execute("UPDATE world_info SET clock=?", (item["kickoff"],))
        audit(c, parent, check_journal=False, validate_results=not forward_enabled(c))


def advance(directory, *, until=None, before_fixture=None, crash=None, max_groups=None):
    if not until and not before_fixture:
        raise ValueError("Choose an explicit fictional date or before-fixture boundary")
    directory = Path(directory).resolve()
    groups = 0
    with writer(directory) as (c, policy):
        audit(c, directory / "parent.sqlite")
        if before_fixture:
            boundary = c.execute(
                "SELECT kickoff,status FROM world_fixtures WHERE key=?",
                (before_fixture,),
            ).fetchone()
            if not boundary or boundary["status"] == "final":
                raise ValueError("Boundary fixture missing or already final")
            limit = boundary["kickoff"]
        else:
            moment(until)
            limit = until
        if moment(limit) < moment(
            c.execute("SELECT clock FROM world_info").fetchone()[0]
        ):
            raise ValueError(
                "Requested boundary predates the committed fictional clock"
            )
        while True:
            if is_readiness(policy):
                from .progression import activate

                activate(c)
            batch = c.execute(
                "SELECT * FROM world_batches WHERE status='claimed' ORDER BY kickoff,key LIMIT 1"
            ).fetchone()
            if batch:
                if (
                    moment(batch["kickoff"]) > moment(limit)
                    or before_fixture
                    and moment(batch["kickoff"]) == moment(limit)
                ):
                    raise ValueError(
                        "A committed batch must be resumed at its original boundary"
                    )
                simulate_pending(c, batch["key"], policy, crash)
                fault(crash, "after_simulation")
                continue
            items = agenda(c)
            if not items:
                break
            first = items[0]
            kickoff = first["kickoff"]
            if (
                moment(kickoff) > moment(limit)
                or before_fixture
                and moment(kickoff) == moment(limit)
            ):
                break
            if first["kind"] == "administrative":
                apply_obligation(c, first, directory / "parent.sqlite")
                continue
            if first["kind"] == "completion":
                apply_batch(c, first["key"], policy, directory / "parent.sqlite", crash)
                fault(crash, "after_commit")
                groups += 1
                if max_groups is not None and groups >= max_groups:
                    break
                continue
            group = [
                r for r in items if r["kind"] == "match" and r["kickoff"] == kickoff
            ]
            claim(c, group, policy)
            fault(crash, "after_claim")
        result = audit(c, directory / "parent.sqlite")
        return {
            **result,
            "clock": c.execute("SELECT clock FROM world_info").fetchone()[0],
            "groups_this_call": groups,
            "official_records_changed": False,
            "promotable": False,
        }


def fixture_preview(c, policy, key):
    row = c.execute(
        "SELECT * FROM world_executions WHERE fixture_key=?", (key,)
    ).fetchone()
    if row:
        data = json.loads(row["input_json"])
        snapshot = codec.snapshot(data["snapshot"])
        config = load_config(
            json.loads(row["config_json"]), policy, data["rules"]["extra_time"]
        )
        seeds = SeedCommitment(**json.loads(row["seed_json"]))
    else:
        f = c.execute("SELECT * FROM world_fixtures WHERE key=?", (key,)).fetchone()
        if not f:
            raise ValueError("Unknown fixture")
        snapshot, _, _ = context(c, f, policy, logical_hash(c))
        config = configuration(policy, f["stage"] == "Final única")
        seeds = commit_seeds(
            snapshot,
            config,
            c.execute("SELECT seed FROM world_info").fetchone()[0] + ":" + key,
        )
    return make_preview(snapshot, prepare(snapshot, config, seeds), config, seeds)


def narrate(directory, key, count=1):
    if not isinstance(count, int) or not 1 <= count <= 20:
        raise ValueError("Narration count must be 1–20")
    with writer(directory) as (c, policy):
        row = c.execute(
            "SELECT * FROM world_executions WHERE fixture_key=? AND status='applied'",
            (key,),
        ).fetchone()
        if not row:
            raise ValueError("No committed result for this fixture")
        bundle = json.loads(row["result_json"])
        if digest(bundle) != row["result_sha256"]:
            raise ValueError("Narration source changed")
        cursor = c.execute(
            "SELECT * FROM world_cursors WHERE fixture_key=?", (key,)
        ).fetchone()
        if cursor and cursor["result_sha256"] != row["result_sha256"]:
            raise ValueError("Cursor/result mismatch")
        position = cursor["sequence"] if cursor else 0
        if not 0 <= position <= len(bundle["events"]):
            raise ValueError("Invalid narration cursor")
        events = bundle["events"][position : position + count]
        public = []
        for e in events:
            e = {**e, "details": dict(e["details"])}
            if e["kind"] == "SHOT":
                e["details"] = {
                    k: v
                    for k, v in e["details"].items()
                    if k not in ("goal", "on_target", "goal_probability")
                }
            public.append(e)
        position += len(events)
        done = position == len(bundle["events"])
        with c:
            c.execute(
                "INSERT OR REPLACE INTO world_cursors VALUES(?,?,?)",
                (key, row["result_sha256"], position),
            )
        response = {
            "scope": SCOPE,
            "fixture_key": key,
            "events": public,
            "postmatch_available": done,
        }
        if done:
            response["postmatch_summary"] = {
                "score": bundle["score"],
                "resolution": bundle["resolution"],
                "performances": bundle["performances"],
            }
        return response
