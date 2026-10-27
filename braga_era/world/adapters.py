"""Adapters explicitly map heterogeneous legacy competitions into one forward namespace."""

from dataclasses import asdict
import json
from ..engine.competitions import CalendarEntry, Progression
from ..history import canonical_json as encode
from .policy import rules_for
from .players import pregame
from .rosters import alias


def calendar_key(comp, event_id):
    return (
        comp.lower()
        + ":"
        + (event_id[4:] if comp == "CDB" and event_id.startswith("CDB:") else event_id)
    )


def install(c):
    names = {r["alias"]: r["key"] for r in c.execute("SELECT * FROM world_clubs")}

    def key(name):
        if not name:
            return None
        if alias(name) not in names:
            raise ValueError("Unresolved club alias: " + name)
        return names[alias(name)]

    for r in c.execute(
        "SELECT * FROM fixtures WHERE competition='Brasileirão 2027' AND status='scheduled' ORDER BY id"
    ).fetchall():
        c.execute(
            "INSERT INTO world_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"league:{r['id']}",
                "LEAGUE",
                2027,
                r["round"],
                None,
                1,
                f"club:{r['home_id']}",
                f"club:{r['away_id']}",
                r["datetime_local"],
                "scheduled",
                "fixtures",
                str(r["id"]),
                "[]",
                None,
                None,
                None,
            ),
        )
    for r in c.execute(
        "SELECT * FROM calendar_events ORDER BY kickoff,event_id"
    ).fetchall():
        comp = r["competition"]
        ref = calendar_key(comp, r["event_id"])
        tie = ref.rsplit(":L", 1)[0] if r["home"] else None
        deps = [calendar_key(comp, d) for d in json.loads(r["depends_json"])]
        c.execute(
            "INSERT INTO world_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ref,
                comp,
                2027,
                r["stage"],
                tie,
                r["leg"],
                key(r["home"]),
                key(r["away"]),
                r["kickoff"],
                "scheduled" if r["home"] else "conditional",
                r["source_table"] or "calendar_events",
                r["source_key"] or r["event_id"],
                encode(deps),
                None,
                None,
                None,
            ),
        )
        if tie and r["leg"] == 1:
            following = None
            if comp == "CDB":
                next_name = c.execute(
                    "SELECT next_tie FROM cdb_2027_bracket WHERE tie_code=?",
                    (r["source_key"],),
                ).fetchone()[0]
                following = "cdb:" + next_name if next_name else None
            c.execute(
                "INSERT INTO world_ties(key,competition,stage,club_a,club_b,next_tie) VALUES(?,?,?,?,?,?)",
                (tie, comp, r["stage"], key(r["home"]), key(r["away"]), following),
            )
    # CDB's known bracket is usable. Continental round-level reservations have no disclosed draw mapping.
    for r in c.execute(
        "SELECT * FROM cdb_2027_bracket WHERE status='pending_qualifiers' ORDER BY tie_code"
    ).fetchall():
        c.execute(
            "INSERT INTO world_ties(key,competition,stage,next_tie,status) VALUES(?,?,?,?,?)",
            (
                "cdb:" + r["tie_code"],
                "CDB",
                r["stage"],
                "cdb:" + r["next_tie"] if r["next_tie"] else None,
                "conditional",
            ),
        )
        c.execute(
            "UPDATE world_fixtures SET tie_key=? WHERE competition='CDB' AND source_key=?",
            ("cdb:" + r["tie_code"], r["tie_code"]),
        )


class Adapter:
    competition = None

    def __init__(self, c, policy):
        self.c = c
        self.policy = policy

    def due_entries(self, as_of):
        return tuple(
            CalendarEntry(
                r["key"],
                r["kickoff"],
                r["competition"],
                r["season"],
                r["status"] == "scheduled",
            )
            for r in self.c.execute(
                "SELECT * FROM world_fixtures WHERE competition=? AND status<>'final' AND kickoff>=? ORDER BY kickoff,key",
                (self.competition, as_of),
            )
        )

    def fixture(self, key):
        r = self.c.execute(
            "SELECT * FROM world_fixtures WHERE key=? AND competition=?",
            (key, self.competition),
        ).fetchone()
        if r is None:
            raise ValueError("Unknown namespaced fixture")
        return r

    def rules_for(self, key):
        f = self.fixture(key)
        return rules_for(
            self.competition,
            f["leg"] == 2 or f["stage"] == "Final única",
            f["stage"] == "Final única",
        )

    def pregame(self, key, world_hash=""):
        f = self.fixture(key)
        if f["status"] != "scheduled":
            raise ValueError("Fixture final or awaiting an unresolved qualifier/draw")
        for d in json.loads(f["depends_json"]):
            dep = self.c.execute(
                "SELECT status FROM world_fixtures WHERE key=?", (d,)
            ).fetchone()
            from .forward_schema import enabled
            from .progression import dependency_done

            if not (
                dependency_done(self.c, d)
                if enabled(self.c)
                else dep and dep[0] == "final"
            ):
                raise ValueError("Unresolved competition dependency: " + d)
        return pregame(self.c, f, self.policy, world_hash)

    def progression(self, result):
        f = self.fixture(result.fixture_key)
        if not f["tie_key"]:
            return Progression(None, None, False, False, ())
        t = self.c.execute(
            "SELECT * FROM world_ties WHERE key=?", (f["tie_key"],)
        ).fetchone()
        a, b = result.score if f["home"] == t["club_a"] else result.score[::-1]
        aggregate = (t["aggregate_a"] + a, t["aggregate_b"] + b)
        decisive = f["leg"] == 2 or f["stage"] == "Final única"
        winner = (
            (
                t["club_a"]
                if aggregate[0] > aggregate[1]
                else t["club_b"] if aggregate[1] > aggregate[0] else None
            )
            if decisive
            else None
        )
        rule = self.rules_for(f["key"])
        tied = decisive and aggregate[0] == aggregate[1]
        return Progression(
            aggregate,
            winner,
            tied and rule.extra_time,
            tied and rule.penalties,
            (t["next_tie"],) if t["next_tie"] else (),
        )

    def apply(self, f, bundle):
        score = bundle["score"]
        self.c.execute(
            "UPDATE world_fixtures SET status='final',home_goals=?,away_goals=?,resolution_json=? WHERE key=? AND status='scheduled'",
            (*score, encode(bundle["resolution"]), f["key"]),
        )
        if f["tie_key"]:
            t = self.c.execute(
                "SELECT * FROM world_ties WHERE key=?", (f["tie_key"],)
            ).fetchone()
            a, b = score if f["home"] == t["club_a"] else score[::-1]
            self.c.execute(
                "UPDATE world_ties SET aggregate_a=aggregate_a+?,aggregate_b=aggregate_b+?,legs_played=legs_played+1,winner=?,status=? WHERE key=?",
                (
                    a,
                    b,
                    bundle["resolution"]["winner"],
                    "final" if bundle["resolution"]["winner"] else "partial",
                    f["tie_key"],
                ),
            )
        self.mirror(f, bundle)
        if self.competition == "CDB":
            self.activate_known_cdb()

    def activate_known_cdb(self):
        for t in self.c.execute(
            "SELECT * FROM world_ties WHERE competition='CDB' AND status='conditional' ORDER BY key"
        ).fetchall():
            parents = self.c.execute(
                "SELECT * FROM world_ties WHERE next_tie=? ORDER BY key", (t["key"],)
            ).fetchall()
            if len(parents) != 2 or any(not p["winner"] for p in parents):
                continue
            a, b = (p["winner"] for p in parents)
            self.c.execute(
                "UPDATE world_ties SET club_a=?,club_b=?,status='scheduled' WHERE key=?",
                (a, b, t["key"]),
            )
            for f in self.c.execute(
                "SELECT * FROM world_fixtures WHERE tie_key=? ORDER BY leg", (t["key"],)
            ).fetchall():
                home, away = (a, b) if f["leg"] == 1 else (b, a)
                self.c.execute(
                    "UPDATE world_fixtures SET home=?,away=?,status='scheduled' WHERE key=?",
                    (home, away, f["key"]),
                )
            names = [
                self.c.execute(
                    "SELECT name FROM world_clubs WHERE key=?", (k,)
                ).fetchone()[0]
                for k in (a, b)
            ]
            self.c.execute(
                "UPDATE cdb_2027_bracket SET club_a=?,club_b=?,first_leg_home=?,second_leg_home=?,status='scheduled' WHERE tie_code=?",
                (*names, *names, t["key"][4:]),
            )

    def mirror(self, f, bundle):
        raise NotImplementedError


class LeagueAdapter(Adapter):
    competition = "LEAGUE"

    def mirror(self, f, b):
        r = b["regulation"]
        shots = b["shots"]
        home, away = b["score"]
        hx = round(sum(s["xg"] for s in shots if s["club_key"] == f["home"]), 4)
        ax = round(sum(s["xg"] for s in shots if s["club_key"] == f["away"]), 4)
        hs = sum(s["club_key"] == f["home"] for s in shots)
        away_shots = len(shots) - hs
        ht = sum(s["club_key"] == f["home"] and s["on_target"] for s in shots)
        at = sum(s["club_key"] == f["away"] and s["on_target"] for s in shots)
        self.c.execute(
            """UPDATE fixtures SET status='final',home_goals=?,away_goals=?,home_xg=?,away_xg=?,home_shots=?,away_shots=?,
            home_sot=?,away_sot=?,home_possession=?,away_possession=?,report=? WHERE id=? AND status='scheduled'""",
            (
                home,
                away,
                hx,
                ax,
                hs,
                away_shots,
                ht,
                at,
                r["possession_home"],
                100 - r["possession_home"],
                "NONCANONICAL DEVELOPMENT TEST",
                int(f["source_key"]),
            ),
        )
        recompute_standings(self.c)


class LibertadoresAdapter(Adapter):
    competition = "LIB"

    def mirror(self, f, b):
        if f["source_table"] != "libertadores_2027_round_of_16":
            return
        winner = (
            self.c.execute(
                "SELECT name FROM world_clubs WHERE key=?", (b["resolution"]["winner"],)
            ).fetchone()
            if b["resolution"]["winner"]
            else None
        )
        column = "leg1_result" if f["leg"] == 1 else "leg2_result"
        self.c.execute(
            f"UPDATE libertadores_2027_round_of_16 SET {column}=?,status=?,winner=? WHERE tie_id=?",
            (
                f"{b['score'][0]}-{b['score'][1]}",
                "completed" if winner else "partial",
                winner[0] if winner else None,
                f["source_key"],
            ),
        )


class SudamericanaAdapter(Adapter):
    competition = "SULA"

    def mirror(self, f, b):
        if f["source_table"] != "sudamericana_2027_playoffs":
            return
        winner = (
            self.c.execute(
                "SELECT name FROM world_clubs WHERE key=?", (b["resolution"]["winner"],)
            ).fetchone()
            if b["resolution"]["winner"]
            else None
        )
        self.c.execute(
            "UPDATE sudamericana_2027_playoffs SET status=?,winner=? WHERE tie_id=?",
            (
                "completed" if winner else "partial",
                winner[0] if winner else None,
                f["source_key"],
            ),
        )


class CopaDoBrasilAdapter(Adapter):
    competition = "CDB"

    def mirror(self, f, b):
        names = [
            self.c.execute("SELECT name FROM world_clubs WHERE key=?", (k,)).fetchone()[
                0
            ]
            for k in (f["home"], f["away"])
        ]
        shots = b["shots"]
        xg = [
            round(sum(s["xg"] for s in shots if s["club_key"] == k), 4)
            for k in (f["home"], f["away"])
        ]
        counts = [
            sum(s["club_key"] == k for s in shots) for k in (f["home"], f["away"])
        ]
        seed = int(b["regulation"]["seeds"]["root_sha256"][:15], 16)
        self.c.execute(
            "INSERT INTO cdb_2027_legs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f["source_key"],
                f["leg"],
                f["kickoff"][:10],
                *names,
                *b["score"],
                *xg,
                *counts,
                seed,
            ),
        )
        winner = (
            self.c.execute(
                "SELECT name FROM world_clubs WHERE key=?", (b["resolution"]["winner"],)
            ).fetchone()
            if b["resolution"]["winner"]
            else None
        )
        self.c.execute(
            "UPDATE cdb_2027_bracket SET status=?,winner=? WHERE tie_code=?",
            (
                "completed" if winner else "partial",
                winner[0] if winner else None,
                f["source_key"],
            ),
        )


ADAPTERS = {
    a.competition: a
    for a in (
        LeagueAdapter,
        CopaDoBrasilAdapter,
        LibertadoresAdapter,
        SudamericanaAdapter,
    )
}


def adapter(c, competition, policy):
    return ADAPTERS[competition](c, policy)


def recompute_standings(c, write=True):
    result = {
        r[0]: dict(points=0, played=0, wins=0, draws=0, losses=0, gf=0, ga=0)
        for r in c.execute("SELECT club_id FROM league_participants WHERE season=2027")
    }
    for f in c.execute(
        "SELECT * FROM fixtures WHERE competition='Brasileirão 2027' AND status='final' ORDER BY id"
    ):
        for own, other, gf, ga in (
            (f["home_id"], f["away_id"], f["home_goals"], f["away_goals"]),
            (f["away_id"], f["home_id"], f["away_goals"], f["home_goals"]),
        ):
            row = result[own]
            row["played"] += 1
            row["gf"] += gf
            row["ga"] += ga
            row["wins"] += int(gf > ga)
            row["draws"] += int(gf == ga)
            row["losses"] += int(gf < ga)
            row["points"] += 3 if gf > ga else int(gf == ga)
    if write:
        for key, row in result.items():
            c.execute(
                "UPDATE clubs SET points=?,played=?,wins=?,draws=?,losses=?,gf=?,ga=? WHERE id=?",
                (*row.values(), key),
            )
    return result
