"""Authenticated imported base for the explicitly approved episode #81 fork."""
from contextlib import closing
import hmac
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

from ..checkpoints import read_json, write_json
from ..db import connect_read_only, file_sha256
from ..forward import sign
from ..history import canonical_json as encode, digest
from ..seasons import fingerprints
from .registered import PROFILE, policy

ACTION = "import_verified_episode81_fork"
REHEARSAL = "rehearse_accepted_timeline"
QUALIFIED = "import_verified_libertadores_2028"
ACTIONS = {ACTION, REHEARSAL, QUALIFIED}
QUALIFIED_CAREER = "the-braga-era-libertadores-2028"
QUALIFIED_SOURCE = "c090fe185089a5fc5a1cf0a748a532ac499dba5abe204fa5282988a54ab68136"
QUALIFIED_ARCHIVE = "70d3e0f2ba8c0f7a1f5759aa1ed973fb80961009e4c336328cb4801db0397dc4"
QUALIFIED_DATABASE = "fd31311d349722283ab550d5c2b9d50449d55835f700e5d1b382935811de629e"
QUALIFIED_SEED = "df032276cfd217ba53484aa4db7890115988e67ff91d9fd1f76f8adb570200f1"
QUALIFIED_CUTOFF = "2028-04-09 17:33:00"
SOURCE = "2ca17c34c366558f854fd00eb3cba9077774de6287f01e377da3259f0a088498"
DETACHED = "b314e9e158f5a1bcfcdc282fe5da5d32b49f1a0ce658a4477dcd856e854091fc"
ARCHIVE = "c25602eeacf3dcf54be56c917b63f8398e077829c2bf979e6a18b98a9c8795b4"
WORLD_BYTES = "83fb24d36da4097980c7e5ee6704f2a986cb416b5442c55ffad5ed47800c53af"
MATCH_RESULT = "b5de76929bd683a224e004e0948c0bccd3ab729fcc6f6186b77dae1e904a14e8"
REPLAY_SEED = "d4853ec560bb64a182d9499af020776570905cca9af26251436339e5d38651d9"


def authenticate(directory, marker, key):
    d = marker["decision"]
    rehearsal = d["action"] == REHEARSAL
    eligible = not rehearsal
    if (d["action"] not in ACTIONS or d["profile"] != PROFILE
            or type(d["test_only"]) is not bool or marker["test_only"] is not d["test_only"]
            or marker["profile"] != PROFILE or marker["acceptance_eligible"] is not eligible
            or marker["policy"] != policy(d["test_only"]) or d["policy_sha256"] != digest(marker["policy"])
            or d["seed_sha256"] != digest(marker["seed"])
            or not hmac.compare_digest(marker["signature"], sign(key, d))
            or file_sha256(directory / "parent.sqlite") != d["parent_sha256"]):
        raise ValueError("Untrusted timeline base")
    if rehearsal:
        if (d["test_only"] is not True or marker["acceptance_eligible"] is not False
                or d["parent_checkpoint"] != d["source_checkpoint"]
                or d["seed_mode"] not in {"same", "alternate"}):
            raise ValueError("Timeline rehearsals are not acceptance eligible")
    elif d["action"] == QUALIFIED:
        validate_qualified_origin(d)
    elif (marker["acceptance_eligible"] is not True or d["source_checkpoint"] != SOURCE
          or d["parent_checkpoint"] != DETACHED or d["archive_sha256"] != ARCHIVE
          or d["parent_sha256"] != WORLD_BYTES or d["result_sha256"] != MATCH_RESULT
          or d["replay_seed_commitment_sha256"] != REPLAY_SEED):
        raise ValueError("Episode #81 origin differs")
    return directory, marker


def validate_qualified_origin(decision):
    if any(decision.get(k) != v for k, v in {
        'action': QUALIFIED, 'career': QUALIFIED_CAREER, 'source_checkpoint': QUALIFIED_SOURCE,
        'parent_checkpoint': QUALIFIED_SOURCE, 'archive_sha256': QUALIFIED_ARCHIVE,
        'parent_sha256': QUALIFIED_DATABASE, 'seed_sha256': QUALIFIED_SEED,
        'revealed_through': QUALIFIED_CUTOFF, 'source_entropy_parent': WORLD_BYTES,
    }.items()):
        raise ValueError('Qualifying import differs from the independently verified archive')


def initialize(source, target, marker, key):
    target.mkdir()
    shutil.copyfile(source, target / "parent.sqlite")
    write_json(target / "development.json", marker)
    authenticate(target, marker, key)
    shutil.copyfile(source, target / "database.sqlite")
    d = marker["decision"]
    with closing(sqlite3.connect(target / "database.sqlite")) as db, db:
        db.execute("UPDATE ms_meta SET parent_checkpoint=?,parent_sha256=?,seed=?,policy_json=?,test_only=?",
                   (d["parent_checkpoint"], d["parent_sha256"], marker["seed"],
                    encode(marker["policy"]), int(marker["test_only"])))


def operations(db):
    return list(db.execute("SELECT * FROM ms_operations ORDER BY sequence"))


def validate(directory, marker, key, *, replay):
    from .store import run
    with connect_read_only(directory / "parent.sqlite") as base, connect_read_only(directory / "database.sqlite") as db:
        decision = marker["decision"]
        if decision["action"] == REHEARSAL and decision["source_entropy_parent"] != base.execute(
                "SELECT parent_sha256 FROM ms_meta").fetchone()[0]:
            raise ValueError("Timeline entropy does not match the inherited database")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Fork database integrity failure")
        if db.execute("SELECT 1 FROM ms_fixtures WHERE status='claimed'").fetchone():
            raise ValueError("Incomplete fork match group")
        inherited = operations(base)
        all_ops = operations(db)
        if all_ops[:len(inherited)] != inherited:
            raise ValueError("Fork operation history changed")
        prior = inherited[-1]["sha256"]
        suffix = all_ops[len(inherited):]
        for i, row in enumerate(suffix, len(inherited) + 1):
            doc = {"request_id": row["request_id"], "kind": row["kind"], "args": json.loads(row["args_json"]),
                   "response": json.loads(row["response_json"]), "previous": prior}
            if (row["sequence"] != i or row["previous_sha256"] != prior or digest(doc) != row["sha256"]
                    or not hmac.compare_digest(sign(key, doc), row["signature"])):
                raise ValueError("Fork operation suffix changed")
            prior = row["sha256"]
        # All completed fixtures and commitments in the accepted base are immutable.
        for old in base.execute("SELECT * FROM ms_executions"):
            if db.execute("SELECT * FROM ms_executions WHERE fixture=?", (old["fixture"],)).fetchone() != old:
                raise ValueError("Fork changed an inherited match execution")
        schema = "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name"
        if db.execute(schema).fetchall() != base.execute(schema).fetchall():
            raise ValueError("Fork changed the accepted schema")
        expected = fingerprints(db)
    if replay:
        with tempfile.TemporaryDirectory(dir=directory.parent, prefix=".fork-replay-") as tmp:
            target = Path(tmp) / "world"
            initialize(directory / "parent.sqlite", target, marker, key)
            for row in suffix:
                if run(target, key, row["request_id"], row["kind"], json.loads(row["args_json"])) != json.loads(row["response_json"]):
                    raise ValueError("Fork independent operation response differs")
            with connect_read_only(target / "database.sqlite") as db:
                if fingerprints(db) != expected:
                    raise ValueError("Fork independent replay differs")
    return {"profile": PROFILE, "ok": True, "test_only": marker["test_only"],
            "acceptance_eligible": marker["acceptance_eligible"],
            "operations": len(all_ops), "world_sha256": digest(expected), "independent_replay": replay}


def status(registry,key):
    from .. import lineage, season_lineage
    from .agenda import event_from_connection
    from .execution import active_engine
    with lineage.access(registry,key) as (c,t):
        info,_=season_lineage.current(c,t,key)
        origin=read_json(info["world"]/"development.json")["decision"]
        if origin["action"]!=ACTION:
            raise ValueError("No episode #81 fork is active")
        with connect_read_only(info["database"]) as db:
            next_vasco=db.execute("""SELECT f.kickoff,e.competition,h.name AS home,a.name AS away
                FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition
                JOIN world_clubs h ON h.key=f.home JOIN world_clubs a ON a.key=f.away
                WHERE f.status!='final' AND 'club:15' IN (f.home,f.away) ORDER BY f.kickoff,f.key LIMIT 1""").fetchone()
            next_event=event_from_connection(db)
            return {"career":t["career"],"checkpoint":info["checkpoint"],"clock":info["clock"],
                    "source_checkpoint":origin["source_checkpoint"],"detached_checkpoint":origin["parent_checkpoint"],
                    "engine_version":active_engine(db) or "braga-headless-1.1.0",
                    "next_vasco":dict(next_vasco) if next_vasco else None,
                    "next_event":{k:next_event[k] for k in ("kind","kickoff")} if next_event else None}
