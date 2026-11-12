"""Exercise the proposed transition using the signed archived TEST 2028 parent."""
import argparse
import gzip
from io import BytesIO
from itertools import groupby
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from braga_era import lineage, season_lineage as sl
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.multiseason import agenda, store
from braga_era.multiseason.authentic import catalogue
from braga_era.multiseason.lifecycle import setup_following
from tools.rehearse_registered_seasons import KEY


def run(source, scratch, groups):
    with TemporaryDirectory(dir=scratch, prefix="authentic-rehearsal-") as directory:
        root = Path(directory)
        registry = root / "registry.sqlite"
        objects = root / "season-objects"
        objects.mkdir()
        with ZipFile(source) as outer:
            note = json.loads(outer.read("NONCANONICAL.json"))
            registry.write_bytes(gzip.decompress(outer.read("registry.sqlite.gz")))
            assert file_sha256(registry) == note["registry_sha256"]
            with ZipFile(BytesIO(outer.read("checkpoint.zip"))) as archive:
                package = json.loads(archive.read("package.json"))
                assert package["metadata"]["test_only"]
                for entry in archive.namelist():
                    if entry.startswith("objects/"):
                        name = Path(entry).name
                        assert sl.objects.HASH.fullmatch(Path(name).stem) and name.endswith(".gz")
                        (objects / name).write_bytes(archive.read(entry))
        with lineage.access(registry, KEY) as (db, trusted):
            assert trusted["test_only"]
            node = package
            while node["metadata"]["season"] != 2028:
                node = sl.document(db, node["metadata"]["parent_node_sha256"])
            sl.verify_node(node, trusted, KEY)
            assert node["manifest"]["operations"][-1]["kind"] == "archive_season"
            state = sl.document(db, node["metadata"]["state_sha256"])
            sl.materialize(db, {"state": state}, root / "world")
        world = root / "world"
        db_path = world / "database.sqlite"
        assert file_sha256(db_path) == node["metadata"]["database_sha256"]
        print("Authenticated TEST parent", digest(node["metadata"]), flush=True)
        with connect_read_only(db_path) as db:
            history = digest([tuple(r) for r in db.execute("""SELECT x.fixture,x.result_sha256
                FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture
                JOIN ms_editions e ON e.id=f.edition WHERE e.season=2028 ORDER BY x.fixture""")])

        def command(kind, **args):
            request = str(uuid5(NAMESPACE_URL, "authentic-audit-1:" + kind + ":" + digest(args)))
            return store.run(world, KEY, request, kind, args)

        command("prepare_season", season=2029)
        setup_following(world, command, 2029, rio_alternative=True, authentic=True)
        with connect_read_only(db_path) as db:
            registered = catalogue(db, 2029)
            names = dict(db.execute("SELECT key,name FROM world_clubs"))
            for comp in ("LEAGUE", "SERIE_B", "CARIOCA", "CDB"):
                clubs = [r[0] for r in db.execute("SELECT club FROM ms_entries WHERE edition=?", (comp+":2029",))]
                assert all(key in registered for key in clubs)
                print(comp, len(clubs), sorted(names[k] for k in clubs)[:20], flush=True)
            for comp in ("LIB", "SULA", "LIB_PRE1", "LIB_PRE2", "SULA_PRE"):
                clubs = [r[0] for r in db.execute("SELECT club FROM ms_qualifications WHERE season=2029 AND competition=?", (comp,))]
                print(comp, len(clubs), sorted(names[k] for k in clubs), flush=True)
            for name in ("River Plate", "Carabobo FC", "Volta Redonda"):
                key = next(key for key in registered if names[key]==name)
                from braga_era.multiseason.authentic import display_names
                aliases = display_names(db,2029)
                players = [(aliases.get(str(r[0]),{}).get("name", p["name"]),p["position"],p["ovr"])
                           for r in db.execute("SELECT id,attributes_json FROM world_players WHERE club_key=? ORDER BY id", (key,))
                           for p in [json.loads(r[1])]]
                print("SQUAD", name, players[:6], flush=True)
        if groups:
            result = agenda.advance(world, KEY, request_id=str(uuid5(NAMESPACE_URL, "authentic-fixtures-audit-1")),
                                    max_groups=groups)
            print("Verified groups", result["groups_completed"], flush=True)
        with connect_read_only(db_path) as db:
            assert history == digest([tuple(r) for r in db.execute("""SELECT x.fixture,x.result_sha256
                FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture
                JOIN ms_editions e ON e.id=f.edition WHERE e.season=2028 ORDER BY x.fixture""")])
            for comp in ("LEAGUE", "SERIE_B", "LOWER"):
                fixtures=list(db.execute("SELECT home,away FROM ms_fixtures WHERE edition=? ORDER BY kickoff,round",(comp+":2029",)))
                if fixtures:
                    runs=max(len(list(run)) for club in {r[0] for r in fixtures}
                             for _,run in groupby(h==club for h,a in fixtures if club in (h,a)))
                    assert runs<=3
                    print("VENUES",comp,len(fixtures),"max run",runs,flush=True)
        print("Logical state", store.validate(world, KEY, replay=False)["world_sha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--groups", type=int, default=0)
    options = parser.parse_args()
    run(options.source, options.scratch.resolve(strict=True), options.groups)
