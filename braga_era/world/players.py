"""One elapsed-time player timeline shared by every competition."""

from dataclasses import replace
from datetime import datetime, timedelta
import json
from ..engine.models import Coach, Team, Snapshot, CompetitionRules
from ..history import canonical_json as encode
from .codec import player


def moment(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is not None:
        raise ValueError(
            "Fictional calendar uses local naive timestamps; offsets are not supported"
        )
    return result


def stamp(value):
    return value.isoformat(sep=" ", timespec="seconds")


def projected(state, kickoff, policy):
    state = dict(state)
    hours = (moment(kickoff) - moment(state["observed_at"])).total_seconds() / 3600
    if hours < 0:
        raise ValueError("Player timeline would move backwards")
    state["fitness"] = round(
        min(100, state["fitness"] + hours / 24 * policy.recovery_per_day), 4
    )
    if state["injury_until"] and moment(state["injury_until"]) <= moment(kickoff):
        state["injury_until"] = None
    return state


def team_at(c, key, competition, kickoff, policy):
    club = c.execute("SELECT * FROM world_clubs WHERE key=?", (key,)).fetchone()
    if club is None:
        raise ValueError("Unknown club identity")
    players = []
    for row in c.execute(
        "SELECT p.*,s.state_json,d.bans AS forward_bans FROM world_players p "
        "LEFT JOIN world_player_state s ON s.player_id=p.id "
        "LEFT JOIN world_discipline d ON d.player_id=p.id AND d.competition=? "
        "WHERE p.club_key=? ORDER BY p.id", (competition,key)
    ):
        p = player(json.loads(row["attributes_json"]))
        s = projected(
            json.loads(row['state_json']),
            kickoff,
            policy,
        )
        reasons = list(p.exclusion_reasons)
        if not s["registered"]:
            reasons.append("not registered")
        if s["injury_unknown"]:
            reasons.append("recorded injury with unknown recovery date")
        if s["injury_until"]:
            reasons.append("injury until " + s["injury_until"])
        if s["contract_start"] and s["contract_start"] > kickoff[:10]:
            reasons.append("contract not started")
        if s["contract_end"] and s["contract_end"] < kickoff[:10]:
            reasons.append("contract expired")
        if row['forward_bans']:
            reasons.append("forward " + competition + " suspension")
        recent = tuple((x["rating"], x["minutes"]) for x in s["recent"][:4])
        players.append(
            replace(
                p,
                club_key=key,
                fitness=s["fitness"],
                morale=s["morale"],
                form=s["form"],
                eligible=not reasons,
                exclusion_reasons=tuple(reasons),
                recent_ratings=recent,
            )
        )
    if len([p for p in players if p.eligible]) < 11:
        raise ValueError(f"{club['name']}: fewer than eleven eligible players")
    coach = (
        Coach("Luan Braga", "4-2-3-1 asymmetric", "4-4-2 midblock", 0.53, 0.65, 0.8)
        if club["name"] == "Vasco"
        else Coach(
            "Modeled autonomous " + club["name"] + " coach",
            "4-3-3",
            "4-4-2",
            0.55 if club["strength"] >= 77 else 0.46,
            0.4,
            1,
        )
    )
    training = list(
        c.execute(
            "SELECT * FROM world_training WHERE club_key=? AND consumed_fixture IS NULL AND starts<=? AND expires>=? ORDER BY id",
            (key, kickoff, kickoff),
        )
    )
    return Team(
        key,
        club["name"],
        club["strength"] + sum(r["quality_delta"] for r in training),
        club["form"],
        tuple(players),
        coach,
    )


def pregame(c, fixture, policy, world_hash):
    archived = tuple(
        r[0]
        for r in c.execute(
            "SELECT archived_id FROM player_identity_resolution ORDER BY archived_id"
        )
    )
    notes = (
        "NONCANONICAL DEVELOPMENT TEST; proposed rosters/rules/player timeline; no official authority",
        "policy=" + policy.fingerprint,
        "historical bans unknown; forward per-competition discipline only",
    )
    return Snapshot(
        fixture["key"],
        fixture["kickoff"],
        c.execute("SELECT clock FROM world_info").fetchone()[0],
        team_at(c, fixture["home"], fixture["competition"], fixture["kickoff"], policy),
        team_at(c, fixture["away"], fixture["competition"], fixture["kickoff"], policy),
        CompetitionRules(
            fixture["competition"],
            progression="world proposal; regulation plus separately validated knockout resolution",
        ),
        world_hash,
        archived,
        False,
        notes,
    )


def apply_players(c, fixture, snapshot, bundle, policy):
    end = stamp(
        moment(fixture["kickoff"]) + timedelta(seconds=bundle["duration_seconds"])
    )
    # Bans are served by the club's next match in this competition, including non-selected players.
    for key in (fixture["home"], fixture["away"]):
        c.execute(
            "UPDATE world_discipline SET bans=max(0,bans-1) WHERE competition=? AND player_id IN (SELECT id FROM world_players WHERE club_key=?)",
            (fixture["competition"], key),
        )
    for p in bundle["performances"]:
        pid = p["player_id"]
        s = json.loads(
            c.execute(
                "SELECT state_json FROM world_player_state WHERE player_id=?", (pid,)
            ).fetchone()[0]
        )
        s.update(
            fitness=p["fitness_after"],
            morale=p["morale_after"],
            form=p["form_after"],
            observed_at=end,
            last_played=end,
        )
        s["recent"] = (
            [
                {
                    "dated": end,
                    "rating": p["rating"],
                    "minutes": p["seconds_played"] / 60,
                    "source": fixture["key"],
                }
            ]
            + s["recent"]
        )[:4]
        if p["injured"]:
            s["injury_until"] = stamp(moment(end) + timedelta(days=5))
        c.execute(
            "UPDATE world_player_state SET state_json=? WHERE player_id=?",
            (encode(s), pid),
        )
        d = c.execute(
            "SELECT yellows,bans FROM world_discipline WHERE player_id=? AND competition=?",
            (pid, fixture["competition"]),
        ).fetchone()
        yellows = (d[0] if d else 0) + p["yellows"]
        bans = (
            (d[1] if d else 0)
            + int(p["red"]) * policy.red_suspension_matches
            + yellows // policy.yellow_threshold
        )
        c.execute(
            "INSERT OR REPLACE INTO world_discipline VALUES(?,?,?,?)",
            (pid, fixture["competition"], yellows % policy.yellow_threshold, bans),
        )
    for key in (fixture["home"], fixture["away"]):
        c.execute(
            "UPDATE world_training SET consumed_fixture=? WHERE club_key=? AND consumed_fixture IS NULL AND starts<=? AND expires>=?",
            (fixture["key"], key, fixture["kickoff"], fixture["kickoff"]),
        )
