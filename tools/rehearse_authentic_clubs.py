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
from braga_era.multiseason.authentic import POLICY
from braga_era.multiseason.lifecycle import setup_following
from tools.rehearse_registered_seasons import KEY


def inherited_history(db):
    return digest([tuple(row) for row in db.execute("""SELECT f.*,x.input_sha256,x.config_json,
            x.seed_json,x.result_sha256 FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition
            LEFT JOIN ms_executions x ON x.fixture=f.key WHERE e.season=2028 ORDER BY f.key""")])


def verify_movements(db):
    from braga_era.multiseason.competitions import standings
    def members(comp):
        return {row[0] for row in db.execute("SELECT club FROM ms_entries WHERE edition=?", (f"{comp}:2030",))}
    a, b, lower = ([row["club"] for row in standings(db, f"{comp}:2029")]
                   for comp in ("LEAGUE", "SERIE_B", "LOWER"))
    assert members("LEAGUE") == set(a[:16]+b[:4])
    assert members("SERIE_B") == set(a[16:]+b[4:16]+lower[:4])
    assert members("LOWER") == set(b[16:]+lower[4:])
    names = dict(db.execute("SELECT key,name FROM world_clubs"))
    print("2030 promotion to A", [names[key] for key in b[:4]],
          "relegation from A", [names[key] for key in a[16:]], flush=True)
    registered = catalogue(db, 2030)
    assert registered == catalogue(db, 2029)
    rows = db.execute("""SELECT competition,club,source_json FROM ms_qualifications
        WHERE season=2030 AND competition IN ('LIB','LIB_PRE1','LIB_PRE2','SULA','SULA_PRE')""").fetchall()
    assert len(rows)==91 and len({row['club'] for row in rows})==91
    assert all(row['club'] in registered for row in rows)
    print("2030 all-real continental entries", len(rows), flush=True)


def registered_recovery(root, registry, node, state):
    """Rebind only the public-key TEST copy to its authenticated archived ancestor."""
    head = digest(node["metadata"])
    parent = root / "archived-parent"
    payload = parent / "payload"
    payload.mkdir(parents=True)
    package = {key: node[key] for key in ("metadata", "manifest", "authorization", "validation")}
    package["state"] = state
    assert digest(package) == node["package_sha256"]
    sl.write_json(payload / "package.json", package)
    sl.write_json(payload / "checkpoint.json", node["metadata"])
    with lineage.access(registry, KEY) as (c, trusted):
        assert trusted["test_only"]
        sl.chain(c, package, trusted, KEY, node)
        assert c.execute("UPDATE accepted SET path=? WHERE checkpoint=?", (str(parent), head)).rowcount == 1
        c.execute("DELETE FROM accepted WHERE generation>?", (node["metadata"]["generation"],))
        c.execute("UPDATE authority SET head=?", (head,))
        c.execute("DELETE FROM parent_claims WHERE parent=?", (head,))
        trusted = lineage.authority(c, KEY)
        with connect_read_only(root / "world/database.sqlite") as db:
            rows = db.execute("""SELECT fixture,result_sha256,json_array_length(result_json,'$.events')
                                 FROM ms_executions WHERE result_json IS NOT NULL""").fetchall()
        c.execute("DELETE FROM cursors")
        c.executemany("INSERT INTO cursors VALUES(?,?,?)", map(tuple, rows))
        lineage.seal_cursors(c, trusted, KEY)
    request = str(uuid5(NAMESPACE_URL, "authentic-registered-recovery-2029"))
    manifest = sl.prepare(registry, KEY, request, [{"kind": "lifecycle_following_authentic",
                          "args": {"scenario": POLICY}}], transition=True)
    signature = lineage.signed(sl.authorization(manifest), KEY)
    sl.authorize(registry, KEY, manifest, signature)
    sl.authorize(registry, KEY, manifest, signature)
    candidate = root / "candidate"

    def interrupted(call, *args, **kwargs):
        try:
            call(*args, **kwargs)
        except RuntimeError as exc:
            if "Injected" not in str(exc):
                raise
        else:
            raise AssertionError("Expected interruption")

    interrupted(sl.execute, registry, KEY, request, candidate, crash="after_operations")
    result = sl.execute(registry, KEY, request, candidate)
    assert result["independent_delta_replay"]
    decision = sl.acceptance_template(registry, KEY, candidate)
    signature = lineage.sign(KEY, decision)
    interrupted(sl.accept, registry, KEY, candidate, decision, signature, crash="before_commit")
    with lineage.access(registry, KEY) as (_, trusted):
        assert trusted["head"] == head
    interrupted(sl.accept, registry, KEY, candidate, decision, signature, crash="after_commit")
    assert sl.accept(registry, KEY, candidate, decision, signature)["checkpoint_sha256"] == result["checkpoint_sha256"]
    try:
        sl.prepare(registry, KEY, str(uuid5(NAMESPACE_URL, "authentic-duplicate")), [
            {"kind": "lifecycle_following_authentic", "args": {"scenario": POLICY}}], transition=True)
    except ValueError as exc:
        assert "Archive the completed season" in str(exc)
    else:
        raise AssertionError("Duplicate transition was accepted")
    archive = root / "authentic-successor.zip"
    exported = sl.export(registry, KEY, candidate, archive)
    restored = sl.restore(registry, KEY, archive, root / "restored")
    assert restored["checkpoint"] == exported["checkpoint"] == result["checkpoint_sha256"]
    print("Registered recovery, export and independent restore passed", restored, flush=True)


def run(source, scratch, groups, full=False, recovery=False):
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
        if recovery:
            registered_recovery(root, registry, node, state)
            return
        with connect_read_only(db_path) as db:
            history = inherited_history(db)

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
        if full:
            for i in range(24):
                if agenda.next_event(world, KEY) is None:
                    break
                try:
                    result = agenda.advance(world, KEY, request_id=str(uuid5(NAMESPACE_URL, f"authentic-full:{i}")),
                                            max_groups=60)
                except ValueError:
                    event=agenda.next_event(world, KEY)
                    print("Rehearsal blocked at", event, flush=True)
                    if event and event["kind"]=="payroll":
                        from braga_era.multiseason.market import payroll_detail
                        with connect_read_only(db_path) as db:
                            available={row[0]:row[1] for row in db.execute("SELECT club,cash_cents-reserve_cents FROM ms_accounts")}
                            print("Underfunded TEST payroll payers", sorted(
                                key for key, amount in payroll_detail(db,event["period"]).items()
                                if available.get(key,0)<amount), flush=True)
                    raise
                with connect_read_only(db_path) as db:
                    finals = db.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]
                print("Full rehearsal", i, result["groups_completed"], finals, flush=True)
            else:
                raise ValueError("2029 agenda did not finish")
            with connect_read_only(db_path) as db:
                competitions = [r[0] for r in db.execute(
                    "SELECT competition FROM ms_editions WHERE season=2029 ORDER BY competition")]
            command("archive_season", season=2029, required_competitions=competitions)
            with connect_read_only(db_path) as db:
                print("2029 finals", [tuple(r) for r in db.execute("""
                    SELECT e.competition,e.champion,count(f.key) FROM ms_editions e
                    LEFT JOIN ms_fixtures f ON f.edition=e.id WHERE e.season=2029
                    GROUP BY e.id ORDER BY e.competition""")], flush=True)
            command("prepare_season", season=2030)
            setup_following(world, command, 2030, rio_alternative=True, authentic=True)
            with connect_read_only(db_path) as db:
                verify_movements(db)
            result = agenda.advance(world, KEY, request_id=str(uuid5(NAMESPACE_URL, "authentic-2030-opening")),
                                    max_groups=40)
            print("2030 groups", result["groups_completed"], flush=True)
        with connect_read_only(db_path) as db:
            assert history == inherited_history(db)
            for comp in ("LEAGUE", "SERIE_B", "LOWER"):
                year = 2030 if full else 2029
                fixtures=list(db.execute("SELECT home,away FROM ms_fixtures WHERE edition=? ORDER BY kickoff,round",(f"{comp}:{year}",)))
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
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--recovery", action="store_true")
    options = parser.parse_args()
    run(options.source, options.scratch.resolve(strict=True), options.groups, options.full, options.recovery)
