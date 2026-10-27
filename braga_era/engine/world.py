"""Read-only adapters for actual recorded squads; missing foreign squads fail closed."""

from dataclasses import replace
from pathlib import Path

from ..db import connect_read_only, file_sha256
from .models import Player, Team, Coach, Snapshot, CompetitionRules


class MissingRoster(ValueError):
    pass


class World:
    def __init__(self, path):
        self.path = Path(path).resolve()

    def _team(self, c, name, archived):
        row = c.execute("SELECT * FROM clubs WHERE name=?", (name,)).fetchone()
        if row is None:
            raise MissingRoster(
                f"{name}: no recorded player roster/club identity; no foreign names or ratings will be invented"
            )
        key = f"club:{row['id']}"
        players = []
        for p in c.execute(
            """SELECT p.*,mf.form_rating FROM players p LEFT JOIN match_form_profile mf ON mf.player_id=p.id
            WHERE p.club_id=? ORDER BY p.id""",
            (row["id"],),
        ):
            reasons = []
            if p["id"] in archived:
                reasons.append("archived historical identity")
            if p["injury"]:
                reasons.append("injury: " + p["injury"])
            if p["fitness"] <= 0:
                reasons.append("unfit")
            recent = tuple(
                (float(r[0]), float(r[1]))
                for r in c.execute(
                    """SELECT pm.rating,pm.minutes FROM player_matches pm
                JOIN fixtures f ON f.id=pm.fixture_id WHERE pm.player_id=? AND f.competition='Brasileirão 2027' AND f.status='final'
                ORDER BY f.datetime_local DESC,f.id DESC LIMIT 4""",
                    (p["id"],),
                )
            )
            players.append(
                Player(
                    p["id"],
                    key,
                    p["name"],
                    p["pos"],
                    p["ovr"],
                    p["attack"],
                    p["defense"],
                    p["passing"],
                    p["physical"],
                    p["composure"],
                    p["goalkeeping"],
                    p["fitness"],
                    p["morale"],
                    p["form_rating"] if p["form_rating"] is not None else 6.55,
                    not reasons,
                    tuple(reasons),
                    recent,
                )
            )
        if len([p for p in players if p.eligible]) < 11:
            raise MissingRoster(f"{name}: fewer than 11 eligible recorded players")
        coach = (
            Coach("Luan Braga", "4-2-3-1 asymmetric", "4-4-2 midblock", 0.53, 0.65, 0.8)
            if name == "Vasco"
            else Coach(
                f"Modeled autonomous {name} coach",
                "4-3-3",
                "4-4-2",
                0.55 if row["strength"] >= 77 else 0.46,
                0.4,
                1.0,
            )
        )
        return Team(key, name, row["strength"], row["form"], tuple(players), coach)

    def load_pregame(self, fixture_id):
        reference = str(fixture_id)
        if reference.isdigit():
            reference = "league:" + reference
        with connect_read_only(self.path) as c:
            meta = dict(c.execute("SELECT key,value FROM meta"))
            archived = tuple(
                r[0]
                for r in c.execute("SELECT archived_id FROM player_identity_resolution")
            )
            if reference.startswith("league:"):
                row = c.execute(
                    """SELECT f.*,h.name home,a.name away FROM fixtures f JOIN clubs h ON h.id=f.home_id
                    JOIN clubs a ON a.id=f.away_id WHERE f.id=?""",
                    (int(reference.split(":")[1]),),
                ).fetchone()
                if row is None:
                    raise ValueError("Unknown fixture")
                if row["status"] != "scheduled":
                    raise ValueError(
                        "Settled fixture cannot be simulated; history is immutable"
                    )
                if not row["datetime_local"]:
                    raise ValueError("Scheduled fixture has no known kickoff")
                home, away, kickoff, competition = (
                    row["home"],
                    row["away"],
                    row["datetime_local"],
                    row["competition"],
                )
            elif reference.startswith("calendar:"):
                row = c.execute(
                    "SELECT * FROM calendar_events WHERE event_id=?",
                    (reference[len("calendar:") :],),
                ).fetchone()
                if row is None:
                    raise ValueError("Unknown calendar fixture")
                if row["status"] != "scheduled" or not row["home"] or not row["away"]:
                    raise ValueError(
                        "Undrawn qualifiers are reservations, not executable fixtures"
                    )
                home, away, kickoff, competition = (
                    row["home"],
                    row["away"],
                    row["kickoff"],
                    row["competition"],
                )
            else:
                raise ValueError(
                    "Use a namespaced league:ID or calendar:EVENT_ID reference"
                )
            return Snapshot(
                reference,
                kickoff,
                meta["current_date"],
                self._team(c, home, archived),
                self._team(c, away, archived),
                CompetitionRules(competition),
                file_sha256(self.path),
                archived,
                False,
                (
                    "Observed checkpoint fitness/form; no intervening games or future recovery assumed",
                    "No canonical suspension register exists; injuries/archive exclusions are enforced, no historical bans are invented",
                ),
            )

    def synthetic(self, home="Vasco", away="Fluminense"):
        with connect_read_only(self.path) as c:
            meta = dict(c.execute("SELECT key,value FROM meta"))
            archived = tuple(
                r[0]
                for r in c.execute("SELECT archived_id FROM player_identity_resolution")
            )
            return Snapshot(
                f"synthetic:{home}:{away}",
                "2027-09-30 16:00",
                meta["current_date"],
                self._team(c, home, archived),
                self._team(c, away, archived),
                CompetitionRules("Synthetic exhibition; no official fixture"),
                file_sha256(self.path),
                archived,
                True,
                (
                    "Synthetic match using recorded squads; not Mirassol R26 or any official result",
                ),
            )

    def first_recorded_fixture(self):
        with connect_read_only(self.path) as c:
            rows = list(
                c.execute(
                    """SELECT f.id FROM fixtures f JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id
                WHERE f.status='scheduled' AND f.competition='Brasileirão 2027' AND h.name<>'Vasco' AND a.name<>'Vasco'
                ORDER BY f.datetime_local,f.id"""
                )
            )
        for row in rows:
            try:
                return self.load_pregame(f"league:{row[0]}")
            except MissingRoster:
                continue
        raise MissingRoster(
            "No scheduled non-Vasco fixture has two eligible recorded squads"
        )
