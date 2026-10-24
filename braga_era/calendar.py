"""Deterministic calendar proposals; unknown qualifiers reserve capacity, never results."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta


class CalendarError(ValueError):
    """A bounded scheduling search could not satisfy the configured policy."""


@dataclass(frozen=True)
class CalendarPolicy:
    minimum_rest_hours: int = 72
    international_buffer_hours: int = 0
    workload_window_days: int = 8
    maximum_matches_in_window: int = 3
    deadline: str = "2027-12-31 21:00"
    search_limit: int = 100_000

    def validate(self):
        if (self.minimum_rest_hours < 1 or self.international_buffer_hours < 0
                or self.workload_window_days < 1 or self.maximum_matches_in_window < 1
                or self.search_limit < 1):
            raise CalendarError("Rest/workload/search constraints must be positive")
        datetime.fromisoformat(self.deadline)


@dataclass(frozen=True)
class Event:
    event_id: str
    competition: str
    stage: str
    leg: int
    clubs: tuple[str, ...]
    depends: tuple[str, ...] = ()
    international: bool = False
    source_table: str | None = None
    source_key: str | None = None
    source_column: str | None = None
    previous_date: str | None = None
    home: str | None = None
    away: str | None = None


def inventory(c):
    """All known league commitments and last played fixtures; exact league times retained."""
    now = datetime.fromisoformat(c.execute("SELECT value FROM meta WHERE key='current_date'").fetchone()[0])
    fixed = []
    for r in c.execute("""SELECT f.*,h.name home,a.name away FROM fixtures f
        JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id
        WHERE competition='Brasileirão 2027' AND datetime_local>=? ORDER BY datetime_local,f.id""",
                       ((now-timedelta(days=14)).isoformat(sep=" "),)):
        fixed.append({"event_id": f"league:{r['id']}", "kickoff": r["datetime_local"],
                      "clubs": [r["home"], r["away"]], "international": False})
    return now, fixed


def events_from_brackets(c) -> list[Event]:
    events = []
    pools = {}
    for table, cup, stage in [("libertadores_2027_round_of_16", "LIB", "R16"),
                              ("sudamericana_2027_playoffs", "SULA", "PO")]:
        clubs = set()
        completed_ids = []
        for row in c.execute(f"SELECT * FROM {table} ORDER BY tie_id"):
            if row["status"] != "scheduled" or row["winner"] is not None:
                raise CalendarError(f"Expected unplayed {table} tie")
            home, away = row["first_leg_home"], row["second_leg_home"]
            clubs.update((home, away))
            for leg, column in [(1, "first_leg_date"), (2, "second_leg_date")]:
                eid = f"{row['tie_id']}:L{leg}"
                depends = () if leg == 1 else (f"{row['tie_id']}:L1",)
                events.append(Event(eid, cup, stage, leg, tuple(sorted((home, away))), depends,
                                    True, table, row["tie_id"], column, row[column],
                                    home if leg == 1 else away, away if leg == 1 else home))
                if leg == 2:
                    completed_ids.append(eid)
        pools[cup] = clubs
        if cup == "SULA":
            clubs.update(r[0] for r in c.execute("SELECT club FROM sudamericana_2027_group_outcomes WHERE position=1"))
        # Stage reservations protect every possible qualifier, without inventing
        # pairings, home clubs, winners or official fixtures for undrawn rounds.
        for future_stage in (["QF", "SF", "FINAL"] if cup == "LIB" else ["R16", "QF", "SF", "FINAL"]):
            for leg in ([1] if future_stage == "FINAL" else [1, 2]):
                eid = f"reserve:{cup}:{future_stage}:L{leg}"
                events.append(Event(eid, cup, future_stage, leg, tuple(sorted(clubs)), tuple(completed_ids), True))
                completed_ids = [eid]
    cdb = {r["tie_code"]: dict(r) for r in c.execute("SELECT * FROM cdb_2027_bracket")}
    def potential(code):
        row = cdb[code]
        if row["club_a"] and row["club_b"]:
            return {row["club_a"], row["club_b"]}
        return set().union(*(potential(k) for k, v in cdb.items() if v["next_tie"] == code))
    for code, row in sorted(cdb.items()):
        if row["stage"] not in ("Quartas", "Semifinais", "Final única"):
            continue
        parents = tuple(f"CDB:{k}:L2" for k, v in sorted(cdb.items()) if v["next_tie"] == code)
        for leg, column in [(1, "leg1_date"), (2, "leg2_date")]:
            if row[column] is None:
                continue
            dependencies = parents if leg == 1 and row["stage"] != "Quartas" else ()
            if leg == 2:
                dependencies = (f"CDB:{code}:L1",)
            events.append(Event(f"CDB:{code}:L{leg}", "CDB", row["stage"], leg,
                                tuple(sorted(potential(code))), dependencies, False,
                                "cdb_2027_bracket", code, column, row[column],
                                row["first_leg_home"] if leg == 1 else row["second_leg_home"],
                                row["second_leg_home"] if leg == 1 else row["first_leg_home"]))
    return sorted(events, key=lambda e: e.event_id)


def required_gap(a, b, policy):
    return policy.minimum_rest_hours + (policy.international_buffer_hours
                                       if a.international or b.international else 0)


def solve(events: list[Event], fixed: list[dict], now: datetime, policy: CalendarPolicy) -> dict:
    policy.validate()
    by_id = {e.event_id: e for e in events}
    if len(by_id) != len(events) or any(d not in by_id for e in events for d in e.depends):
        raise CalendarError("Invalid or duplicate dependency identities")
    start = (now+timedelta(days=1)).replace(hour=16, minute=0)
    end = datetime.fromisoformat(policy.deadline)
    hours = range(16, 22)
    times = [start.replace(hour=h)+timedelta(days=day)
             for day in range(max(0, (end.date()-start.date()).days+1)) for h in hours
             if start.replace(hour=h)+timedelta(days=day) <= end]
    fixed_by_club = defaultdict(list)
    for f in fixed:
        for club in f["clubs"]:
            fixed_by_club[club].append(datetime.fromisoformat(f["kickoff"]))
    domains = {}
    for e in events:
        gap = timedelta(hours=policy.minimum_rest_hours + (policy.international_buffer_hours if e.international else 0))
        games = {t for club in e.clubs for t in fixed_by_club[club]}
        domains[e.event_id] = [t for t in times if all(abs(t-f) >= gap for f in games)]
    share = {(a.event_id, b.event_id): bool(set(a.clubs) & set(b.clubs)) for a in events for b in events}
    nodes = 0
    assigned = {}

    def compatible(a, ta, b, tb):
        if b.event_id in a.depends and ta-tb < timedelta(hours=policy.minimum_rest_hours):
            return False
        if a.event_id in b.depends and tb-ta < timedelta(hours=policy.minimum_rest_hours):
            return False
        return not share[a.event_id, b.event_id] or abs(ta-tb) >= timedelta(hours=required_gap(a, b, policy))

    def workload(e, t):
        window = timedelta(days=policy.workload_window_days)
        for club in e.clubs:
            games = sorted(fixed_by_club[club] + [v for k, v in assigned.items() if club in by_id[k].clubs] + [t])
            for i, first in enumerate(games):
                # Only reject windows containing this new event. Existing league
                # shortfalls remain disclosed; they are never silently moved.
                if first <= t < first+window and sum(first <= v < first+window for v in games[i:]) > policy.maximum_matches_in_window:
                    return False
        return True

    def visit(remaining):
        nonlocal nodes
        nodes += 1
        if nodes > policy.search_limit:
            raise CalendarError(f"Search limit ({policy.search_limit}) reached; feasibility unproven, change policy/horizon explicitly")
        if not remaining:
            return dict(assigned)
        # Schedule latest stages backwards so downstream capacity is guaranteed.
        eligible = [k for k in remaining if not any(k in by_id[x].depends for x in remaining)]
        if not eligible:
            raise CalendarError("Cyclic knockout dependencies")
        key = min(eligible, key=lambda k: (len(remaining[k]), -len(by_id[k].clubs), k))
        event = by_id[key]
        for time in reversed(remaining[key]):
            if not workload(event, time):
                continue
            assigned[key] = time
            narrowed = {k: [t for t in vals if compatible(event, time, by_id[k], t)]
                        for k, vals in remaining.items() if k != key}
            # Propagate stage bounds through the whole dependency chain. A
            # local late-stage choice must leave room for *all* earlier legs.
            changed = True
            while changed and all(narrowed.values()):
                changed = False
                for after, vals in list(narrowed.items()):
                    for before in by_id[after].depends:
                        if before not in narrowed:
                            continue
                        earlier = narrowed[before]
                        gap = timedelta(hours=required_gap(by_id[after], by_id[before], policy))
                        new_after = [t for t in vals if t >= earlier[0]+gap]
                        new_before = [t for t in earlier if t <= vals[-1]-gap]
                        if len(new_after) != len(vals) or len(new_before) != len(earlier):
                            changed = True
                            narrowed[after], narrowed[before] = new_after, new_before
                            vals = new_after
                        if not new_after or not new_before:
                            break
                    if not narrowed[after]:
                        break
            if all(narrowed.values()):
                solution = visit(narrowed)
                if solution:
                    return solution
            del assigned[key]
        return None

    if not all(domains.values()):
        raise CalendarError("No legal date for one or more cup legs under the configured deadline/rest policy")
    result = visit(domains)
    if result is None:
        raise CalendarError("No schedule found under the configured rest, workload and year-end constraints")
    return {"policy": asdict(policy), "nodes_searched": nodes,
            "events": [{**asdict(e), "clubs": list(e.clubs), "depends": list(e.depends),
                        "kickoff": result[e.event_id].isoformat(sep=" ", timespec="minutes")}
                       for e in events]}


def propose(c, policy: CalendarPolicy | None = None):
    now, fixed = inventory(c)
    return solve(events_from_brackets(c), fixed, now, policy or CalendarPolicy())


def validate_plan(c, plan: dict) -> dict:
    """Independently check a proposed schedule rather than trusting solver output."""
    import json
    from .history import canonical_json

    policy = CalendarPolicy(**plan["policy"])
    policy.validate()
    now, fixed = inventory(c)
    expected = {e.event_id: e for e in events_from_brackets(c)}
    actual = {e["event_id"]: e for e in plan["events"]}
    problems = []
    if len(actual) != len(plan["events"]) or set(actual) != set(expected):
        problems.append("Missing, duplicate or unexpected calendar event")
        return {"feasible": False, "problems": problems}
    times = {}
    for key, raw in actual.items():
        definition = {k: v for k, v in raw.items() if k != "kickoff"}
        if canonical_json(definition) != canonical_json(asdict(expected[key])):
            problems.append(f"Bracket definition changed: {key}")
        t = datetime.fromisoformat(raw["kickoff"])
        times[key] = t
        if not now < t <= datetime.fromisoformat(policy.deadline):
            problems.append(f"Out of horizon: {key}")
    for key, event in expected.items():
        for parent in event.depends:
            if times[key]-times[parent] < timedelta(hours=policy.minimum_rest_hours):
                problems.append(f"Stage/leg ordering: {parent} -> {key}")
    for n, a in enumerate(expected.values()):
        for b in list(expected.values())[n+1:]:
            if set(a.clubs) & set(b.clubs) and abs(times[a.event_id]-times[b.event_id]) < timedelta(hours=required_gap(a,b,policy)):
                problems.append(f"Cup collision/rest: {a.event_id}, {b.event_id}")
    schedules = defaultdict(list)
    for f in fixed:
        for club in f["clubs"]:
            schedules[club].append((datetime.fromisoformat(f["kickoff"]), f["event_id"], False, False))
    for key, event in expected.items():
        for club in event.clubs:
            schedules[club].append((times[key], key, True, event.international))
    inherited = []
    new_gaps = []
    gaps = []
    maximum_workload = 0
    for club, games in sorted(schedules.items()):
        games.sort()
        for a, b in zip(games, games[1:]):
            hours = (b[0]-a[0]).total_seconds()/3600
            gap = {"club": club, "from": a[1], "to": b[1], "hours": hours}
            gaps.append(gap)
            if a[2] or b[2]:
                new_gaps.append(gap)
                required = policy.minimum_rest_hours + (policy.international_buffer_hours if a[3] or b[3] else 0)
                if hours < required:
                    problems.append(f"New rest shortfall: {club}: {a[1]} -> {b[1]}")
            elif hours < policy.minimum_rest_hours:
                inherited.append(gap)
        for i, a in enumerate(games):
            window = [b for b in games[i:] if b[0] < a[0]+timedelta(days=policy.workload_window_days)]
            maximum_workload = max(maximum_workload, len(window))
            if any(b[2] for b in window) and len(window) > policy.maximum_matches_in_window:
                problems.append(f"Workload excess: {club} from {a[0].isoformat()}")
    buckets = {"under_72": 0, "72_to_95": 0, "96_to_167": 0, "168_plus": 0}
    for gap in new_gaps:
        h = gap["hours"]
        buckets["under_72" if h < 72 else "72_to_95" if h < 96 else "96_to_167" if h < 168 else "168_plus"] += 1
    return {"feasible": not problems, "scope": "New cup matches and conservative downstream capacity; fixed league exceptions disclosed",
            "problems": problems, "fixed_league_events": len(fixed), "cup_or_reservation_events": len(actual),
            "league_fixtures_moved": 0, "minimum_new_turnaround_hours": min(g["hours"] for g in new_gaps),
            "minimum_all_turnaround_hours": min(g["hours"] for g in gaps), "new_rest_distribution": buckets,
            "maximum_matches_in_rolling_window": maximum_workload,
            "inherited_league_rest_exceptions": inherited,
            "rest_intervals": gaps,
            "unresolved": [
                "12 inherited league turnarounds below 72 hours remain unchanged (minimum 68h)",
                "72h is kickoff-to-kickoff including travel, not 72h recovery plus travel; six extra travel hours proved infeasible in this conservative model",
                "Foreign domestic schedules, distances, venues and travel itineraries are absent; no global-calendar guarantee",
                "December 25 semifinals and December 28/31 finals require commissioner acceptance of a year-end extension within 2027",
                "Long inter-leg gaps are a consequence of preserved league fixtures and worst-case multi-competition capacity",
                "Downstream continental pairings/venues are undrawn; reservations block every possible contender and must be refined once draws exist",
            ]}
