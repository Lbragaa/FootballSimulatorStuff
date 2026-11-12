"""Opt-in TEST registry and eligibility policy for a future season."""
from dataclasses import asdict, replace
import json
from random import Random

from ..history import canonical_json as encode, digest
from ..world import player_names
from ..world.policy import WorldPolicy
from ..world.rosters import alias, modeled_squad
from .club_catalogue import ALIASES, entries

POLICY = "authentic-clubs-development-1"
SCHEDULE = "balanced-venues-2"
APPROVAL = "record_authentic_transition_authorization"


def permitted(c, year):
    return bool(c.execute("SELECT test_only FROM ms_meta").fetchone()[0] or
                c.execute("SELECT 1 FROM ms_pools WHERE id=? AND competition='TRANSITION_POLICY'",
                          (f"authorized:{POLICY}:{year}",)).fetchone())


def record_authorization(c, args):
    from .competitions import required
    from .registered import PROFILE
    from .prizes import CONFIG_SHA256, POLICY as PRIZES
    economy = 'prize_policy' in args
    required(args, "season policy prize_policy prize_schedule_sha256" if economy else "season policy")
    if economy and (args['prize_policy'], args['prize_schedule_sha256']) != (PRIZES, CONFIG_SHA256):
        raise ValueError("Exact competition economy authorization required")
    year = args["season"]
    if (type(year) is not int or year < 2029 or args["policy"] != POLICY
            or c.execute("SELECT profile FROM ms_meta").fetchone()[0] != PROFILE
            or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'", (year,)).fetchone()
            or c.execute("SELECT 1 FROM ms_editions WHERE season=?", (year,)).fetchone()):
        raise ValueError("Exact registered season policy authorization required")
    c.execute("INSERT INTO ms_pools VALUES(?,?,?,?,?)",
              (f"authorized:{POLICY}:{year}", year, "TRANSITION_POLICY", encode(args), POLICY))
    return args


def commit_schedule(c, args):
    from .competitions import required
    required(args, "season policy")
    year = args["season"]
    if (type(year) is not int or year < 2029 or args["policy"] != SCHEDULE
            or not permitted(c, year)
            or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'", (year,)).fetchone()
            or c.execute("""SELECT 1 FROM ms_fixtures f JOIN ms_editions e ON f.edition=e.id
                         WHERE e.season=? AND e.competition IN ('LEAGUE','SERIE_B','LOWER')""",(year,)).fetchone()
            or c.execute("SELECT 1 FROM ms_pools WHERE id=?", (f"{SCHEDULE}:{year}",)).fetchone()):
        raise ValueError("New TEST scheduling policy requires an uncommitted future national calendar")
    c.execute("INSERT INTO ms_pools VALUES(?,?,?,?,?)",
              (f"{SCHEDULE}:{year}", year, "VENUE_POLICY", encode(args), SCHEDULE))
    return {"season": year, "policy": SCHEDULE, "test_only": bool(c.execute("SELECT test_only FROM ms_meta").fetchone()[0])}


def catalogue(c, year):
    row = c.execute("SELECT clubs_json FROM ms_pools WHERE id=?", (f"{POLICY}:{year}",)).fetchone()
    return json.loads(row[0]) if row else {}


def display_names(c, year):
    row = c.execute("""SELECT clubs_json FROM ms_pools WHERE competition='PLAYER_DISPLAY'
                       AND season<=? ORDER BY season DESC LIMIT 1""", (year,)).fetchone()
    return json.loads(row[0]) if row else {}


def apply_names(team, names):
    if not names:
        return team
    return replace(team, players=tuple(replace(p, name=names[str(p.id)]["name"])
                   if str(p.id) in names else p for p in team.players))


def opening_liquidity_allowed(c, key, year):
    row = c.execute("SELECT provenance_json FROM world_clubs WHERE key=?", (key,)).fetchone()
    origin = json.loads(row[0]) if row else {}
    return (key != "club:15" and permitted(c, year)
            and origin.get("source") == POLICY and origin.get("effective") == f"{year}-01-01"
            and not c.execute("SELECT 1 FROM ms_accounts WHERE club=?", (key,)).fetchone())


def install(c, args):
    from .competitions import required
    from .market import advance_time
    required(args, "season policy")
    year = args["season"]
    if (type(year) is not int or year < 2029 or args["policy"] != POLICY
            or not permitted(c, year)
            or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'", (year,)).fetchone()
            or c.execute("SELECT 1 FROM ms_editions WHERE season=?", (year,)).fetchone()
            or catalogue(c, year)):
        raise ValueError("Exact future TEST preseason and new catalogue required")
    dated = f"{year}-01-01"
    advance_time(c, dated + " 00:00:00")
    seed = c.execute("SELECT seed FROM ms_meta").fetchone()[0]
    old = {r["alias"]: r for r in c.execute("SELECT * FROM world_clubs")}
    known = {}
    created = 0
    for country, state, name, strength in entries():
        matches = [old[k] for k in {alias(n) for n in (name, *ALIASES.get(name, ()))} if k in old]
        if len(matches) > 1 or matches and matches[0]["country"] not in (None, country):
            raise ValueError("Ambiguous or conflicting club identity: " + name)
        key = matches[0]["key"] if matches else "real:" + digest([country, state, alias(name)])[:16]
        if key in known:
            raise ValueError("Duplicate catalogue identity: " + name)
        known[key] = {"country": country, "state": state, "name": name, "prior": strength,
                      "aliases": list(ALIASES.get(name, ()))}
        if matches:
            continue
        provenance = {"source": POLICY, "effective": dated, "canonical": False, **known[key]}
        c.execute("INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)",
                  (key, name, alias(name), None, country, strength, 0, encode(provenance)))
        used = set()
        for player in modeled_squad(key, name, strength, WorldPolicy()):
            display, nationality = player_names.generate(seed, player.id, country, used)
            used.add(display)
            player = replace(player, name=display)
            origin = {"club_policy": POLICY, "name_policy": player_names.POLICY,
                      "nationality": nationality, "modeled": True, "canonical": False}
            c.execute("INSERT INTO world_players VALUES(?,?,?,?,?,?)",
                      (player.id, key, None, 1, encode(asdict(player)), encode(origin)))
            c.execute("INSERT INTO world_player_state VALUES(?,?)", (player.id, encode({
                "fitness": player.fitness, "morale": player.morale, "form": player.form,
                "observed_at": dated + " 00:00:00", "last_played": None, "injury_until": None,
                "injury_unknown": False, "registered": True, "contract_start": dated,
                "contract_end": dated[:4] + "-12-31", "recent": [],
            })))
        created += 1
    c.execute("INSERT INTO ms_pools VALUES(?,?,?,?,?)",
              (f"{POLICY}:{year}", year, "CLUB_CATALOGUE", encode(known), POLICY))
    display = display_names(c, year-1)
    for key, club in known.items():
        rows = c.execute("SELECT * FROM world_players WHERE club_key=? ORDER BY id", (key,)).fetchall()
        people = [(row, json.loads(row["attributes_json"])["name"]) for row in rows]
        used = {display.get(str(row["id"]), {}).get("name", name) for row, name in people}
        for row, name in people:
            pid = str(row["id"])
            if pid not in display and row["modeled"] and row["source_id"] is None and name.startswith("Fictional "):
                chosen, nationality = player_names.generate(seed, row["id"], club["country"], used)
                display[pid] = {"name": chosen, "nationality": nationality, "original": name}
                used.add(chosen)
    c.execute("INSERT INTO ms_pools VALUES(?,?,?,?,?)",
              (f"{player_names.POLICY}:{year}", year, "PLAYER_DISPLAY", encode(display), player_names.POLICY))
    return {"policy": POLICY, "season": year, "catalogue_sha256": digest(known),
            "registered": len(known), "new_clubs": created, "forward_player_aliases": len(display),
            "test_only": bool(c.execute("SELECT test_only FROM ms_meta").fetchone()[0])}


def order(c, country, year):
    """Fictional national order, with overlap in strength and reproducible upsets."""
    clubs = catalogue(c, year)
    seed = c.execute("SELECT seed FROM ms_meta").fetchone()[0]
    strengths = dict(c.execute("SELECT key,strength FROM world_clubs"))
    # Continental performance informs qualification without mutating inherited ratings.
    titles = dict(c.execute("""SELECT champion,count(*) FROM ms_editions
         WHERE season BETWEEN ? AND ? AND competition IN ('LIB','SULA') AND champion IS NOT NULL
         GROUP BY champion""", (year - 3, year - 1)))
    def score(key):
        rng = Random(int(digest([POLICY, seed, year, country, key]), 16))
        return strengths[key] + min(2, titles.get(key, 0)) + rng.uniform(-10, 10)
    return sorted((key for key in clubs if clubs[key]["country"] == country),
                  key=lambda key: (-score(key), key))


def division_replacements(c, year, routes):
    clubs = catalogue(c, year)
    if not clubs:
        raise ValueError("Committed real club catalogue required")
    occupied = {key for entries in routes.values() for key, _ in entries if key in clubs}
    strength = dict(c.execute("SELECT key,strength FROM world_clubs"))
    reserve = iter(sorted((key for key, entry in clubs.items()
                           if entry["country"] == "BRA" and key not in occupied),
                          key=lambda key: (-strength[key], key)))
    for entries in routes.values():
        for index, (key, source) in enumerate(entries):
            if key not in clubs:
                replacement = next(reserve, None)
                if not replacement:
                    raise ValueError("Insufficient real Brazilian replacement inventory")
                entries[index] = (replacement, {"type": "authentic_transition_admission",
                                                 "vacated_club": key, "sporting_source": source})
    return routes
