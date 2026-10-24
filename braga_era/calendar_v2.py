"""Task 02B scheduling: hard holidays, bounded return legs and explicit strategies.

The rejected v1 solver/profile stays intact for archival verification. These
models search disclosed finite grids; infeasibility is not a proof about every
possible real-world calendar or unknown foreign domestic competitions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta

from .calendar import CalendarError, Event, events_from_brackets, inventory
from .history import canonical_json


@dataclass(frozen=True)
class Policy:
    minimum_rest_hours: int = 72
    international_buffer_hours: int = 0
    workload_window_days: int = 8
    maximum_matches_in_window: int = 3
    maximum_leg_interval_days: int = 14
    maximum_initial_delay_days: int = 35
    blackout_start_month_day: str = "12-22"
    blackout_end_month_day: str = "01-05"
    deadline: str = "2028-01-31 22:00"
    kickoff_first_hour: int = 16
    kickoff_last_hour: int = 22
    search_limit: int = 2_000

    def validate(self):
        if (self.minimum_rest_hours < 72 or self.international_buffer_hours < 0
                or self.maximum_leg_interval_days < 3 or self.maximum_initial_delay_days < 1 or self.workload_window_days < 1
                or self.maximum_matches_in_window < 1 or self.search_limit < 1
                or not 0 <= self.kickoff_first_hour <= self.kickoff_last_hour <= 23):
            raise CalendarError("Invalid policy; the 72-hour rest floor cannot be weakened")
        datetime.fromisoformat(self.deadline)
        for value in (self.blackout_start_month_day, self.blackout_end_month_day):
            datetime.strptime("2000-"+value, "%Y-%m-%d")

    def blacked_out(self, value: datetime) -> bool:
        day = value.strftime("%m-%d")
        start, end = self.blackout_start_month_day, self.blackout_end_month_day
        return start <= day <= end if start <= end else day >= start or day <= end


def _gap(a: Event, b: Event, policy: Policy):
    return policy.minimum_rest_hours + (policy.international_buffer_hours if a.international or b.international else 0)


def _same_tie(a: Event, b: Event):
    return a.leg != b.leg and a.event_id.rsplit(":L", 1)[0] == b.event_id.rsplit(":L", 1)[0]


def search(events: list[Event], fixed: list[dict], now: datetime, policy: Policy) -> dict:
    policy.validate()
    by_id = {e.event_id: e for e in events}
    if len(by_id) != len(events) or any(d not in by_id for e in events for d in e.depends):
        raise CalendarError("Invalid event/dependency inventory")
    # Integer hours make forward checking inexpensive and portable.
    epoch = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(policy.deadline)
    times = [day*24+h for day in range(1, max(0, (end.date()-epoch.date()).days+1))
             for h in range(policy.kickoff_first_hour, policy.kickoff_last_hour+1)
             if epoch+timedelta(hours=day*24+h) <= end and not policy.blacked_out(epoch+timedelta(hours=day*24+h))]
    fixed_by_club = defaultdict(list)
    for f in fixed:
        t = (datetime.fromisoformat(f["kickoff"])-epoch).total_seconds()/3600
        for club in f["clubs"]:
            fixed_by_club[club].append(t)
    domains = {}
    for event in events:
        gap = policy.minimum_rest_hours + (policy.international_buffer_hours if event.international else 0)
        commitments = {t for club in event.clubs for t in fixed_by_club[club]}
        domains[event.event_id] = [t for t in times if all(abs(t-f) >= gap for f in commitments)]
        if event.leg == 1 and event.source_table and not event.depends:
            deadline=(now+timedelta(days=policy.maximum_initial_delay_days)-epoch).total_seconds()/3600
            domains[event.event_id] = [t for t in domains[event.event_id] if t <= deadline]
    shares = {(a.event_id, b.event_id): bool(set(a.clubs) & set(b.clubs)) for a in events for b in events}
    dependencies = [(e.event_id, d) for e in events for d in e.depends]
    leg_limit = policy.maximum_leg_interval_days*24
    assigned = {}
    nodes = 0

    def propagate(remaining):
        again = True
        while again and all(remaining.values()):
            again = False
            for after, before in dependencies:
                if after not in remaining or before not in remaining:
                    continue
                a, b = remaining[after], remaining[before]
                gap = _gap(by_id[after], by_id[before], policy)
                low_a, high_b = b[0]+gap, a[-1]-gap
                high_a, low_b = a[-1], b[0]
                if _same_tie(by_id[after], by_id[before]):
                    high_a, low_b = min(high_a, b[-1]+leg_limit), max(low_b, a[0]-leg_limit)
                aa = [t for t in a if low_a <= t <= high_a]
                bb = [t for t in b if low_b <= t <= high_b]
                if len(aa) != len(a) or len(bb) != len(b):
                    remaining[after], remaining[before] = aa, bb
                    again = True
                if not aa or not bb:
                    return False
        return all(remaining.values())

    def compatible(a, ta, b, tb):
        if b.event_id in a.depends and ta-tb < _gap(a,b,policy):
            return False
        if a.event_id in b.depends and tb-ta < _gap(a,b,policy):
            return False
        if _same_tie(a,b) and abs(ta-tb) > leg_limit:
            return False
        return not shares[a.event_id,b.event_id] or abs(ta-tb) >= _gap(a,b,policy)

    def workload(event, time):
        window = policy.workload_window_days*24
        for club in event.clubs:
            games = sorted(fixed_by_club[club]+[v for k,v in assigned.items() if club in by_id[k].clubs]+[time])
            for i, first in enumerate(games):
                if first <= time < first+window and sum(v < first+window for v in games[i:]) > policy.maximum_matches_in_window:
                    return False
        return True

    def visit(remaining):
        nonlocal nodes
        nodes += 1
        if nodes > policy.search_limit:
            raise CalendarError(f"Search limit {policy.search_limit} reached; feasibility remains unproven")
        if not remaining:
            return dict(assigned)
        eligible = [k for k in remaining if not any(k in by_id[x].depends for x in remaining)]
        if not eligible:
            raise CalendarError("Cyclic dependency graph")
        key = min(eligible, key=lambda k:(len(remaining[k]), -len(by_id[k].clubs), k))
        event = by_id[key]
        for time in reversed(remaining[key]):
            if not workload(event, time):
                continue
            assigned[key] = time
            narrowed = {k:[t for t in values if compatible(event,time,by_id[k],t)] for k,values in remaining.items() if k != key}
            if propagate(narrowed):
                result = visit(narrowed)
                if result is not None:
                    return result
            del assigned[key]
        return None

    if not propagate(domains):
        raise CalendarError("Infeasible in this model: holiday, fixed-fixture, dependency or maximum-leg-gap bounds empty a domain")
    solution = visit(domains)
    if solution is None:
        raise CalendarError("Infeasible on the disclosed hourly grid under all configured constraints")
    return {"revision":"v2", "policy":asdict(policy), "nodes_searched":nodes,
            "events":[{**asdict(e), "clubs":list(e.clubs), "depends":list(e.depends),
                       "kickoff":(epoch+timedelta(hours=solution[e.event_id])).isoformat(sep=" ",timespec="minutes")}
                      for e in events], "league_adjustments":[]}


def _league_blocks(c, fixed):
    """Disclosed controlled-adjustment family, not exhaustive arbitrary rescheduling.

    Remaining league rounds use compact same-kickoff blocks, keeping round order.
    Mirassol-Vasco is pinned separately and can never be moved by this family.
    """
    protected = c.execute("""SELECT f.id FROM fixtures f JOIN clubs h ON h.id=f.home_id
        JOIN clubs a ON a.id=f.away_id WHERE competition='Brasileirão 2027' AND round='R26'
        AND h.name='Mirassol' AND a.name='Vasco'""").fetchone()[0]
    movable = [dict(r) for r in c.execute("""SELECT f.*,h.name home,a.name away FROM fixtures f
        JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id
        WHERE competition='Brasileirão 2027' AND status='scheduled' AND f.id<>? ORDER BY f.id""", (protected,))]
    moving_ids = {f"league:{r['id']}" for r in movable}
    retained = [f for f in fixed if f["event_id"] not in moving_ids]
    blocks = []
    for number in range(26,39):
        group = [r for r in movable if r["round"] == f"R{number}"]
        clubs = tuple(sorted({t for r in group for t in (r["home"],r["away"])}))
        blocks.append(Event(f"league-block:R{number}:L1", "LEAGUE",f"R{number}",1,clubs,
                            () if number == 26 else (f"league-block:R{number-1}:L1",)))
    return blocks, retained, movable


def propose(c, strategy="C", policy: Policy | None=None):
    if strategy not in ("A","B","C"):
        raise CalendarError("Unknown calendar strategy")
    now, fixed = inventory(c)
    policy = policy or Policy(deadline="2028-01-15 22:00" if strategy == "C" else "2027-12-21 22:00")
    if strategy == "B":
        return balanced_league_adjustment(c, policy)
    events = events_from_brackets(c)
    result = search(sorted(events,key=lambda e:e.event_id),fixed,now,policy)
    result["strategy"] = strategy
    return result


def balanced_league_adjustment(c, policy: Policy):
    """A transparent 2027 family: compact congestion weeks, then restore dates.

    This is a constructive feasibility witness, not a claim to globally minimize
    league moves. All original dates are tried again in two deterministic orders.
    No tie winners or future continental draws are assumed.
    """
    league_dates = ["10-03","10-09","10-18","10-24","10-31","11-03","11-06",
                    "11-15","11-18","11-21","11-28","12-11","12-18"]
    cup_dates = ["09-30","10-06","10-12","10-15","10-21","10-27","11-09",
                 "11-12","11-24","12-01","12-04","12-07","12-14","12-21"]
    slots = {"LIB":{"R16":(0,1),"QF":(4,5),"SF":(8,9),"FINAL":(11,)},
             "SULA":{"PO":(0,1),"R16":(4,5),"QF":(8,9),"SF":(11,12),"FINAL":(13,)},
             "CDB":{"Quartas":(2,3),"Semifinais":(6,7),"Final única":(10,)}}
    events=[]
    for e in events_from_brackets(c):
        index=slots[e.competition][e.stage][e.leg-1]
        events.append({**asdict(e),"clubs":list(e.clubs),"depends":list(e.depends),
                       "kickoff":f"2027-{cup_dates[index]} 16:00"})
    moves=[]
    for r in c.execute("""SELECT f.*,h.name home,a.name away FROM fixtures f JOIN clubs h ON h.id=f.home_id
        JOIN clubs a ON a.id=f.away_id WHERE competition='Brasileirão 2027' AND status='scheduled' ORDER BY f.id"""):
        if r['round']=='R26' and r['home']=='Mirassol' and r['away']=='Vasco':
            continue
        after=f"2027-{league_dates[int(r['round'][1:])-26]} 16:00"
        if after != r['datetime_local']:
            moves.append({"fixture_id":r['id'],"before":r['datetime_local'],"after":after,
                          "reason":"Open bounded cup windows, compact congested league rounds; protect Mirassol-Vasco"})
    plan={"revision":"v2","strategy":"B","method":"balanced_round_windows_then_original_date_restoration",
          "policy":asdict(policy),"nodes_searched":0,"events":events,"league_adjustments":moves}
    initial=validate(c,plan)
    if not initial['feasible']:
        raise CalendarError("Balanced league family is infeasible under this policy: "+str(initial['problems'][:4]))
    # Revert moves only when the full independent checker proves no newly
    # introduced violation. Repeat until neither order restores another fixture.
    again=True
    while again:
        again=False
        for reverse in (True,False):
            for move in sorted(list(plan['league_adjustments']),key=lambda r:r['fixture_id'],reverse=reverse):
                candidate={**plan,"league_adjustments":[r for r in plan['league_adjustments'] if r['fixture_id']!=move['fixture_id']]}
                if validate(c,candidate)['feasible']:
                    plan=candidate
                    again=True
    plan['league_adjustments'].sort(key=lambda r:r['fixture_id'])
    return plan


def validate(c, plan):
    policy = Policy(**plan["policy"])
    policy.validate()
    now, original_fixed = inventory(c)
    expected = {e.event_id:e for e in events_from_brackets(c)}
    actual = {e["event_id"]:e for e in plan["events"]}
    problems = []
    if set(actual) != set(expected) or len(actual) != len(plan["events"]):
        return {"feasible":False,"problems":["Event inventory differs from original bracket"]}
    times = {}
    for key,event in actual.items():
        if canonical_json({k:v for k,v in event.items() if k != "kickoff"}) != canonical_json(asdict(expected[key])):
            problems.append(f"Bracket definition changed: {key}")
        t = datetime.fromisoformat(event["kickoff"])
        times[key] = t
        if not now < t <= datetime.fromisoformat(policy.deadline) or policy.blacked_out(t):
            problems.append(f"Horizon/holiday violation: {key}")
        if not policy.kickoff_first_hour<=t.hour<=policy.kickoff_last_hour or t.minute or t.second:
            problems.append(f"Kickoff outside disclosed grid: {key}")
        if expected[key].leg == 1 and expected[key].source_table and not expected[key].depends and t > now+timedelta(days=policy.maximum_initial_delay_days):
            problems.append(f"Overdue opening stage deferred too long: {key}")
    adjustments = {r["fixture_id"]:r for r in plan.get("league_adjustments",[])}
    if len(adjustments) != len(plan.get("league_adjustments",[])):
        problems.append("Duplicate league adjustment")
    if plan["strategy"] != "B" and adjustments:
        problems.append("League changes outside controlled strategy")
    fixed = []
    permitted_ids = set()
    for row in original_fixed:
        fid = int(row["event_id"].split(":")[1])
        f = dict(row)
        if fid in adjustments:
            r = c.execute("SELECT * FROM fixtures WHERE id=?",(fid,)).fetchone()
            move = adjustments[fid]
            if r["status"] != "scheduled" or move["before"] != r["datetime_local"] or (
                    r["round"] == "R26" and set(f["clubs"]) == {"Mirassol","Vasco"}):
                problems.append(f"Unauthorized league move: {fid}")
            f["kickoff"] = move["after"]
            t = datetime.fromisoformat(f["kickoff"])
            if t <= now or t > datetime.fromisoformat(policy.deadline) or policy.blacked_out(t):
                problems.append(f"Invalid moved league date: {fid}")
            permitted_ids.add(fid)
        fixed.append(f)
    if set(adjustments) != permitted_ids:
        problems.append("Unknown or historical league adjustment")
    leg_intervals=[];stage_waits=[]
    for a in expected.values():
        for parent in a.depends:
            gap=(times[a.event_id]-times[parent]).total_seconds()/3600
            if gap < _gap(a,expected[parent],policy):
                problems.append(f"Stage order/rest: {parent} -> {a.event_id}")
            if _same_tie(a,expected[parent]):
                leg_intervals.append({"tie":a.event_id.rsplit(":L",1)[0],"days":gap/24})
                if gap > policy.maximum_leg_interval_days*24:
                    problems.append(f"Return leg too late: {a.event_id}")
            elif a.stage != expected[parent].stage:
                stage_waits.append({"from":parent,"to":a.event_id,"days":gap/24})
    schedules=defaultdict(list)
    original_pairs=set()
    old_by_club=defaultdict(list)
    for f in original_fixed:
        for club in f["clubs"]:
            old_by_club[club].append((datetime.fromisoformat(f["kickoff"]),f["event_id"]))
    for club,games in old_by_club.items():
        games.sort()
        for a,b in zip(games,games[1:]):
            if (b[0]-a[0]).total_seconds()/3600 < policy.minimum_rest_hours:
                original_pairs.add((club,a[1],b[1],a[0],b[0]))
    for f in fixed:
        changed=int(f["event_id"].split(":")[1]) in adjustments
        for club in f["clubs"]:
            schedules[club].append((datetime.fromisoformat(f["kickoff"]),f["event_id"],False,changed))
    for key,e in expected.items():
        for club in e.clubs:
            schedules[club].append((times[key],key,e.international,True))
    inherited=[];rest=[];new_shortfalls=[];max_workload=0
    for club,games in sorted(schedules.items()):
        games.sort()
        for a,b in zip(games,games[1:]):
            h=(b[0]-a[0]).total_seconds()/3600
            record={"club":club,"from":a[1],"to":b[1],"hours":h,"involves_change":a[3] or b[3]}
            rest.append(record)
            required=policy.minimum_rest_hours+(policy.international_buffer_hours if a[2] or b[2] else 0)
            if h < required:
                if not (a[3] or b[3]) and (club,a[1],b[1],a[0],b[0]) in original_pairs:
                    inherited.append(record)
                else:
                    new_shortfalls.append(record)
        for i,a in enumerate(games):
            group=[b for b in games[i:] if b[0] < a[0]+timedelta(days=policy.workload_window_days)]
            max_workload=max(max_workload,len(group))
            if any(b[3] for b in group) and len(group)>policy.maximum_matches_in_window:
                problems.append(f"New workload excess: {club} from {a[0]}")
        # Future league rounds must remain in chronological order for each club.
        league=[(int(k.split(':')[1]),t) for t,k,_,_ in games if k.startswith('league:')]
        rounds=[(c.execute('SELECT round FROM fixtures WHERE id=?',(fid,)).fetchone()[0],t) for fid,t in league]
        if any(int(a[0][1:])>=int(b[0][1:]) for a,b in zip(rounds,rounds[1:])):
            problems.append(f"League round order changed: {club}")
    problems.extend(f"New rest shortfall: {r['club']} {r['from']} -> {r['to']}" for r in new_shortfalls)
    end=max(times.values())
    calendar_end=max([end]+[datetime.fromisoformat(f['kickoff']) for f in fixed])
    changed_rest=[r for r in rest if r['involves_change']]
    return {"feasible":not problems,"problems":problems,"strategy":plan['strategy'],
        "holiday_conflicts":sum(policy.blacked_out(t) for t in times.values()),
        "league_fixtures_moved":len(adjustments),"new_rest_shortfalls":new_shortfalls,
        "inherited_league_rest_exceptions":inherited,"rest_intervals":rest,
        "minimum_new_turnaround_hours":min(r['hours'] for r in changed_rest),
        "international_buffer_hours":policy.international_buffer_hours,
        "maximum_matches_in_rolling_window":max_workload,"leg_intervals":leg_intervals,
        "maximum_leg_interval_days":max(r['days'] for r in leg_intervals),
        "stage_waits":stage_waits,"maximum_stage_wait_days":max(r['days'] for r in stage_waits),
        "completion":end.isoformat(sep=' ',timespec='minutes'),
        "calendar_completion":calendar_end.isoformat(sep=' ',timespec='minutes'),
        "extension_days":max(0,(end.date()-datetime(2027,12,21).date()).days),
        "reservations_are_conditional":True,
        "unresolved":["Foreign domestic schedules and actual routes/venues are absent; the travel buffer is a conservative proxy",
            "Undrawn rounds reserve every possible qualifier; refine capacity only after recorded draws/results",
            "Early-2028 postseason requires commissioner approval and explicit season/contract/preseason/finance handling" if end.year>2027 else "Controlled future league moves require acceptance of the complete before/after date inventory"]}


def realism_score(report):
    if not report['feasible']:
        return None
    new=[r for r in report['rest_intervals'] if r['involves_change']]
    tight=sum(r['hours']<96 for r in new)/len(new)
    components={"stability":max(0,100-0.7*report['league_fixtures_moved']),
        "congestion":100-50*tight,"travel":100 if report['international_buffer_hours']>=6 else 70,
        "return_leg_spacing":max(0,100-5*max(0,report['maximum_leg_interval_days']-7)),
        "duration":max(0,100-2*report['extension_days']),"holidays":100 if not report['holiday_conflicts'] else 0,
        "stage_continuity":max(0,100-2*max(0,report['maximum_stage_wait_days']-14))}
    weights={"stability":.20,"congestion":.20,"travel":.15,"return_leg_spacing":.10,"duration":.10,"holidays":.10,"stage_continuity":.15}
    return {"total":round(sum(components[k]*weights[k] for k in weights),2),
            "components":{k:round(v,2) for k,v in components.items()},"weights":weights,
            "meaning":"Transparent engineering comparison heuristic, not a calibrated football realism statistic"}


def explore(c):
    results=[]
    for strategy in ("A","B","C"):
        try:
            plan=propose(c,strategy,Policy(deadline="2028-01-15 22:00" if strategy=="C" else "2027-12-21 22:00"))
            report=validate(c,plan)
            results.append({"strategy":strategy,"status":"feasible" if report['feasible'] else "validation_failed",
                            "plan":plan,"feasibility":report,"realism_score":realism_score(report)})
        except CalendarError as error:
            results.append({"strategy":strategy,"status":"search_limit" if 'Search limit' in str(error) else "infeasible_model",
                            "reason":str(error),"realism_score":None})
    viable=[r for r in results if r['status']=='feasible']
    return {"alternatives":results,"recommendation":max(viable,key=lambda r:r['realism_score']['total'])['strategy'] if viable else None}
