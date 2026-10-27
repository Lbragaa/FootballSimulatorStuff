"""Stable, explicitly modeled foreign squads from authenticated fictional-world evidence."""

from dataclasses import asdict
import hashlib
import json
import random
import unicodedata
from ..engine.models import Player
from ..history import canonical_json as encode, digest


def alias(name):
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", name).casefold()
            if not unicodedata.combining(c)
        ).split()
    )


def stable_id(key, slot):
    return 1_000_000_000 + int(
        hashlib.sha256(f"{key}:player:{slot}".encode()).hexdigest()[:12], 16
    )


def club_key(name):
    return "modeled:" + hashlib.sha256(alias(name).encode()).hexdigest()[:16]


def modeled_squad(key, name, strength, policy):
    rng = random.Random(
        int(digest({"club": key, "power": strength, "policy": asdict(policy)}), 16)
    )
    positions = ["GK"] * 3 + ["DF"] * 8 + ["MF"] * 7 + ["FW"] * 5
    positions += [rng.choice(("DF", "MF", "FW")) for _ in range(1 + rng.randrange(5))]
    out = []
    for slot, pos in enumerate(positions, 1):
        ovr = round(max(52, min(88, strength - 2 + rng.gauss(0, 3.6))), 1)

        def skill(delta=0):
            return round(max(15, min(95, ovr + delta + rng.uniform(-4, 4))), 1)

        p = Player(
            stable_id(key, slot),
            key,
            f"Fictional {name} {pos}-{slot:02}",
            pos,
            ovr,
            skill(
                4 if pos == "FW" else -8 if pos == "DF" else -40 if pos == "GK" else 0
            ),
            skill(
                4 if pos == "DF" else -12 if pos == "FW" else -35 if pos == "GK" else 0
            ),
            skill(3 if pos == "MF" else -5),
            skill(),
            skill(),
            skill(3) if pos == "GK" else round(rng.uniform(15, 30), 1),
            rng.randint(87, 98),
            rng.randint(55, 77),
            6.55,
        )
        out.append(p)
    return tuple(out)


def evidence(c):
    known = {alias(r["name"]): dict(r) for r in c.execute("SELECT * FROM clubs")}
    records = {}
    for r in c.execute("SELECT * FROM libertadores_2027_participants ORDER BY club"):
        if alias(r["club"]) in known:
            continue
        records[alias(r["club"])] = {
            "name": r["club"],
            "strength": r["power"],
            "country": r["country"],
            "evidence": {"table": "libertadores_2027_participants", "row": dict(r)},
            "assumption": "recorded fictional club power; individual attributes/depth are proposed",
        }
    for r in c.execute("SELECT * FROM sudamericana_2027_groups ORDER BY club"):
        a = alias(r["club"])
        if a in known or a in records:
            continue
        # No recorded SULA power column exists: disclose a pot and results based prior.
        strength = round(
            68 + 2 * (5 - r["pot"]) + max(-1, min(1, (r["points"] - 9) * 0.15)), 2
        )
        records[a] = {
            "name": r["club"],
            "strength": strength,
            "country": None,
            "evidence": {"table": "sudamericana_2027_groups", "row": dict(r)},
            "assumption": "PROPOSAL: power=68+2*(5-pot)+clamp(.15*(group points-9),-1,1); nationality unknown",
        }
    return tuple(records[a] for a in sorted(records))


def historical_recent(c, pid):
    rows = []
    for r in c.execute(
        """SELECT f.datetime_local dated,pm.rating,pm.minutes,'league/main' source FROM player_matches pm
        JOIN fixtures f ON f.id=pm.fixture_id WHERE pm.player_id=? AND f.status='final'
        AND (f.competition IN ('Brasileirão','Brasileirão 2027') OR f.competition LIKE '%Carioca%')""",
        (pid,),
    ):
        if r["dated"] and len(r["dated"]) >= 10 and r["dated"][4] == "-":
            rows.append(dict(r))
    for r in c.execute(
        """SELECT l.dated,p.rating,p.minutes,'CDB' source FROM cdb_2027_player_performance p
        JOIN cdb_2027_legs l ON l.tie_code=p.tie_code AND l.leg=p.leg WHERE p.player_id=?""",
        (pid,),
    ):
        rows.append(dict(r))
    for r in c.execute(
        """SELECT f.dated,p.rating,p.minutes,'SULA' source FROM continental_player_matches p
        JOIN sudamericana_2027_fixtures f ON f.id=p.fixture_id WHERE p.player_id=? AND f.status='final'""",
        (pid,),
    ):
        rows.append(dict(r))
    rows.sort(key=lambda r: (r["dated"], r["source"]), reverse=True)
    return rows[:4]


def install(c, policy, as_of):
    for r in c.execute("SELECT * FROM clubs ORDER BY id").fetchall():
        c.execute(
            "INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)",
            (
                f"club:{r['id']}",
                r["name"],
                alias(r["name"]),
                r["id"],
                "BRA",
                r["strength"],
                r["form"],
                encode({"source": "clubs", "id": r["id"]}),
            ),
        )
    for r in c.execute("SELECT * FROM players ORDER BY id").fetchall():
        recent = historical_recent(c, r["id"])
        form = c.execute(
            "SELECT form_rating FROM match_form_profile WHERE player_id=?", (r["id"],)
        ).fetchone()
        excluded = r["id"] in {
            x[0]
            for x in c.execute("SELECT archived_id FROM player_identity_resolution")
        }
        p = Player(
            r["id"],
            f"club:{r['club_id']}",
            r["name"],
            r["pos"],
            r["ovr"],
            r["attack"],
            r["defense"],
            r["passing"],
            r["physical"],
            r["composure"],
            r["goalkeeping"],
            r["fitness"],
            r["morale"],
            form[0] if form else 6.55,
            not excluded,
            ("archived historical identity",) if excluded else (),
            tuple((x["rating"], x["minutes"]) for x in recent),
        )
        c.execute(
            "INSERT INTO world_players VALUES(?,?,?,?,?,?)",
            (
                p.id,
                p.club_key,
                p.id,
                0,
                encode(asdict(p)),
                encode(
                    {
                        "source": "players",
                        "recent_actual_appearances": recent,
                        "unknown_dates_excluded": True,
                    }
                ),
            ),
        )
        contract = c.execute(
            "SELECT contract_start,contract_end FROM transfer_contracts WHERE player_id=?",
            (p.id,),
        ).fetchone()
        state = {
            "fitness": p.fitness,
            "morale": p.morale,
            "form": p.form,
            "observed_at": as_of,
            "last_played": recent[0]["dated"] if recent else None,
            "injury_until": None,
            "injury_unknown": bool(r["injury"]),
            "registered": not excluded,
            "contract_start": contract[0] if contract else None,
            "contract_end": contract[1] if contract else None,
            "recent": recent,
        }
        c.execute("INSERT INTO world_player_state VALUES(?,?)", (p.id, encode(state)))
    for e in evidence(c):
        key = club_key(e["name"])
        provenance = {
            **e,
            "policy": asdict(policy),
            "modeled": True,
            "canonical_approval": False,
        }
        c.execute(
            "INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)",
            (
                key,
                e["name"],
                alias(e["name"]),
                None,
                e["country"],
                e["strength"],
                0,
                encode(provenance),
            ),
        )
        for p in modeled_squad(key, e["name"], e["strength"], policy):
            c.execute(
                "INSERT INTO world_players VALUES(?,?,?,?,?,?)",
                (p.id, key, None, 1, encode(asdict(p)), encode(provenance)),
            )
            state = {
                "fitness": p.fitness,
                "morale": p.morale,
                "form": p.form,
                "observed_at": as_of,
                "last_played": None,
                "injury_until": None,
                "injury_unknown": False,
                "registered": True,
                "contract_start": as_of[:10],
                "contract_end": "2027-12-31",
                "recent": [],
            }
            c.execute(
                "INSERT INTO world_player_state VALUES(?,?)", (p.id, encode(state))
            )


def distribution(c):
    rows = []
    for club in c.execute(
        "SELECT * FROM world_clubs WHERE source_id IS NULL ORDER BY key"
    ):
        players = [
            json.loads(r[0])
            for r in c.execute(
                "SELECT attributes_json FROM world_players WHERE club_key=? ORDER BY id",
                (club["key"],),
            )
        ]
        rows.append(
            {
                "club_key": club["key"],
                "name": club["name"],
                "strength": club["strength"],
                "depth": len(players),
                "mean_ovr": round(sum(p["ovr"] for p in players) / len(players), 3),
                "positions": {
                    pos: sum(p["position"] == pos for p in players)
                    for pos in ("GK", "DF", "MF", "FW")
                },
                "roster_sha256": digest(players),
                "canonical_approval": False,
            }
        )
    return rows
