"""Committed stage draws on approved reservations; all policies remain proposals."""

import json
import random
from ..history import canonical_json as encode, digest
from .storage import transaction
from .rosters import alias


def reservation_draw(c, key):
    f = c.execute(
        "SELECT competition,stage FROM world_fixtures WHERE key=?", (key,)
    ).fetchone()
    return (
        c.execute(
            "SELECT * FROM world_draws WHERE key=? AND status='activated'",
            (f"{f[0]}:{f[1]}",),
        ).fetchone()
        if f
        else None
    )


def dependency_done(c, key):
    f = c.execute(
        "SELECT status,competition,stage,leg FROM world_fixtures WHERE key=?", (key,)
    ).fetchone()
    if not f:
        return False
    if f[0] == "final":
        return True
    draw = reservation_draw(c, key)
    if not draw:
        return False
    rows = c.execute(
        "SELECT status FROM world_fixtures WHERE competition=? AND stage=? AND leg=? AND home IS NOT NULL",
        (f[1], f[2], f[3]),
    ).fetchall()
    return bool(rows) and all(r[0] == "final" for r in rows)


def pairings(commitment):
    rng = random.Random(int(commitment["seed_sha256"], 16))
    winners = sorted(commitment["qualifiers"])
    if len(winners) != len(set(winners)) or len(winners) < 2 or len(winners) % 2:
        raise ValueError("Duplicate or invalid draw qualifiers")
    seeded = commitment["seeded"]
    if seeded:
        first = sorted(set(winners) - set(seeded))
        second = sorted(seeded)
        if len(first) != len(second) or set(seeded) - set(winners):
            raise ValueError("Invalid seeded draw pools")
        rng.shuffle(first)
        rng.shuffle(second)
        return [list(p) for p in zip(first, second)]
    rng.shuffle(winners)
    return [winners[i : i + 2] for i in range(0, len(winners), 2)]


def activate(c):
    """Persist draw input and RNG commitment in a separate transaction before draws."""
    stages = c.execute(
        "SELECT competition,stage,min(kickoff) kickoff FROM world_fixtures WHERE key LIKE '%:reserve:%' GROUP BY competition,stage ORDER BY kickoff,competition"
    ).fetchall()
    for stage in stages:
        comp, name = stage["competition"], stage["stage"]
        key = f"{comp}:{name}"
        stored = c.execute("SELECT * FROM world_draws WHERE key=?", (key,)).fetchone()
        if stored and stored["status"] == "activated":
            continue
        reservations = c.execute(
            "SELECT * FROM world_fixtures WHERE competition=? AND stage=? AND key LIKE '%:reserve:%' ORDER BY leg",
            (comp, name),
        ).fetchall()
        deps = json.loads(reservations[0]["depends_json"])
        if not all(dependency_done(c, d) for d in deps):
            continue
        if not stored:
            previous = {"QF": "R16", "SF": "QF", "FINAL": "SF", "R16": "PO"}[name]
            ties = c.execute(
                "SELECT key,winner,status FROM world_ties WHERE competition=? AND stage=? ORDER BY key",
                (comp, previous),
            ).fetchall()
            if not ties or any(r["status"] != "final" or not r["winner"] for r in ties):
                raise ValueError("Draw dependency lacks a qualified club: " + key)
            qualifiers = [r["winner"] for r in ties]
            seeded = []
            if comp == "SULA" and name == "R16":
                lookup = {
                    r["alias"]: r["key"] for r in c.execute("SELECT * FROM world_clubs")
                }
                seeded = [
                    lookup[alias(r[0])]
                    for r in c.execute(
                        "SELECT club FROM sudamericana_2027_group_outcomes WHERE position=1 ORDER BY group_id"
                    )
                ]
                qualifiers += seeded
            expected = {"R16": 16, "QF": 8, "SF": 4, "FINAL": 2}[name]
            if len(qualifiers) != expected or len(set(qualifiers)) != expected:
                raise ValueError("Invalid qualification inventory: " + key)
            seed = c.execute("SELECT seed FROM world_info").fetchone()[0]
            commitment = {
                "version": "continental-stage-draw-1",
                "stage": key,
                "qualifiers": sorted(qualifiers),
                "seeded": sorted(seeded),
                "evidence": [dict(t) for t in ties],
                "seed_sha256": digest(
                    {
                        "namespace": "NONCANONICAL-stage-draw",
                        "root": seed,
                        "stage": key,
                        "qualifiers": sorted(qualifiers),
                    }
                ),
            }
            with transaction(c, "draw-commit:" + key):
                c.execute(
                    "INSERT INTO world_draws VALUES(?,?,?,?,?,NULL)",
                    (key, comp, name, encode(commitment), "committed"),
                )
        else:
            commitment = json.loads(stored["commitment_json"])
        pairs = pairings(commitment)
        with transaction(c, "draw-activate:" + key):
            for i, (a, b) in enumerate(pairs, 1):
                tie = f"{comp.lower()}:{name}-{i:02}"
                fixture_stage = "Final única" if name == "FINAL" else name
                c.execute(
                    "INSERT INTO world_ties(key,competition,stage,club_a,club_b) VALUES(?,?,?,?,?)",
                    (tie, comp, fixture_stage, a, b),
                )
                for reservation in reservations:
                    leg = reservation["leg"]
                    home, away = (a, b) if leg == 1 else (b, a)
                    dependencies = [
                        d
                        for d in json.loads(reservation["depends_json"])
                        if d not in {r["key"] for r in reservations}
                    ]
                    if leg == 2:
                        dependencies.append(tie + ":L1")
                    c.execute(
                        "INSERT INTO world_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            tie + f":L{leg}",
                            comp,
                            2027,
                            fixture_stage,
                            tie,
                            leg,
                            home,
                            away,
                            reservation["kickoff"],
                            "scheduled",
                            "calendar_events",
                            reservation["source_key"],
                            encode(dependencies),
                            None,
                            None,
                            None,
                        ),
                    )
            c.execute(
                "UPDATE world_draws SET status='activated',pairings_json=? WHERE key=?",
                (encode(pairs), key),
            )
            from .audit import rest_inventory

            rest_inventory(c)
            validate(c)
    champions(c)


def champions(c):
    with transaction(c, "championship-reconciliation"):
        for tie in c.execute(
            "SELECT * FROM world_ties WHERE stage='Final única' AND status='final'"
        ).fetchall():
            c.execute(
                "INSERT OR IGNORE INTO world_champions VALUES(?,?,?)",
                (
                    tie["competition"],
                    tie["winner"],
                    encode({"tie": tie["key"], "winner": tie["winner"]}),
                ),
            )
        if (
            c.execute(
                "SELECT count(*) FROM fixtures WHERE competition='Brasileirão 2027' AND status='final'"
            ).fetchone()[0]
            == 380
        ):
            winner = c.execute(
                "SELECT c.id FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027 ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name LIMIT 1"
            ).fetchone()[0]
            c.execute(
                "INSERT OR IGNORE INTO world_champions VALUES('LEAGUE',?,?)",
                (
                    f"club:{winner}",
                    encode({"fixtures": 380, "ranking": "points,wins,GD,GF,name"}),
                ),
            )


def validate(c):
    from .adapters import calendar_key
    from .rosters import alias

    clubs = {r["alias"]: r["key"] for r in c.execute("SELECT * FROM world_clubs")}
    for row in c.execute("SELECT * FROM calendar_events"):
        f = c.execute(
            "SELECT * FROM world_fixtures WHERE key=?",
            (calendar_key(row["competition"], row["event_id"]),),
        ).fetchone()
        if not f or (f["competition"], f["stage"], f["leg"], f["kickoff"]) != (
            row["competition"],
            row["stage"],
            row["leg"],
            row["kickoff"],
        ):
            raise ValueError("World/approved calendar reservation mismatch")
        if row["home"] and (f["home"], f["away"]) != (
            clubs[alias(row["home"])],
            clubs[alias(row["away"])],
        ):
            raise ValueError("Previously established cup pairing changed")
    # Native scheduled metadata and the approved reservation clock remain the
    # reference, even if an attacker re-seals an overlay journal.
    for f in c.execute("SELECT * FROM world_fixtures WHERE competition='LEAGUE'"):
        native = c.execute(
            "SELECT * FROM fixtures WHERE id=?", (f["source_key"],)
        ).fetchone()
        if not native or (f["home"], f["away"], f["kickoff"], f["stage"]) != (
            f"club:{native['home_id']}",
            f"club:{native['away_id']}",
            native["datetime_local"],
            native["round"],
        ):
            raise ValueError("World/native fixture identity or clock mismatch")
    for draw in c.execute("SELECT * FROM world_draws"):
        inputs = json.loads(draw["commitment_json"])
        if draw["status"] == "activated":
            pairs = pairings(inputs)
            if pairs != json.loads(draw["pairings_json"]):
                raise ValueError("Committed draw replay mismatch")
            comp, stage = draw["competition"], draw["stage"]
            seen = []
            for i, pair in enumerate(pairs, 1):
                t = c.execute(
                    "SELECT * FROM world_ties WHERE key=?",
                    (f"{comp.lower()}:{stage}-{i:02}",),
                ).fetchone()
                if not t or [t["club_a"], t["club_b"]] != pair:
                    raise ValueError("Draw/bracket participant mismatch")
                seen += pair
            if sorted(seen) != sorted(inputs["qualifiers"]):
                raise ValueError("Missing or phantom qualifiers")
            reservations = c.execute(
                "SELECT * FROM world_fixtures WHERE competition=? AND stage=? AND key LIKE '%:reserve:%' ORDER BY leg",
                (comp, stage),
            ).fetchall()
            for i, (a, b) in enumerate(pairs, 1):
                tie = f"{comp.lower()}:{stage}-{i:02}"
                for reservation in reservations:
                    f = c.execute(
                        "SELECT * FROM world_fixtures WHERE key=?",
                        (tie + f":L{reservation['leg']}",),
                    ).fetchone()
                    orientation = (a, b) if reservation["leg"] == 1 else (b, a)
                    if (
                        not f
                        or (f["home"], f["away"]) != orientation
                        or f["kickoff"] != reservation["kickoff"]
                    ):
                        raise ValueError("Draw fixture orientation/calendar mismatch")
                    approved = c.execute(
                        "SELECT kickoff FROM calendar_events WHERE event_id=?",
                        (reservation["source_key"],),
                    ).fetchone()
                    if not approved or approved[0] != reservation["kickoff"]:
                        raise ValueError("Reserved calendar was altered")
    for champion in c.execute(
        "SELECT * FROM world_champions WHERE competition<>'LEAGUE'"
    ):
        tie = c.execute(
            "SELECT * FROM world_ties WHERE key=?",
            (json.loads(champion["evidence_json"])["tie"],),
        ).fetchone()
        if not tie or tie["status"] != "final" or tie["winner"] != champion["club_key"]:
            raise ValueError("Champion lacks a completed final")
