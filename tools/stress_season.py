"""Full 2027 NONCANONICAL season; fixed seed, crash/resume, portable evidence."""

import argparse
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.world.storage import create
from braga_era.world.policy import ReadinessPolicy
from braga_era.world.runner import advance, InjectedCrash, fixture_preview
from braga_era.world.packages import export_world, fingerprints
from braga_era.world.storage import writer
from braga_era.world.audit import audit
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.checkpoints import write_json, restore_checkpoint


def run(parent, directory, seed, package=True):
    directory = Path(directory)
    if not directory.exists():
        create(parent, directory, seed, ReadinessPolicy())
    # Exercise real persisted commitments, then resume without replacing any seed.
    with connect_read_only(directory / "database.sqlite") as c:
        fresh = c.execute("SELECT count(*) FROM world_executions").fetchone()[0] == 0
    if fresh:
        try:
            advance(directory, until="2027-09-30 23:59", crash="after_result")
        except InjectedCrash:
            pass
    with connect_read_only(directory / "database.sqlite") as c:
        committed = {
            r["fixture_key"]: [r["input_sha256"], r["seed_json"], r["result_sha256"]]
            for r in c.execute("SELECT * FROM world_executions")
        }
    # Pregame handoff contains no future result/table.
    with connect_read_only(directory / "database.sqlite") as c:
        clock = c.execute("SELECT clock FROM world_info").fetchone()[0]
    if clock < "2027-10-03 16:00":
        advance(directory, until="2027-09-30 23:59")
        with writer(directory) as (c, policy):
            # Find the protected fixture from native identities, never assume home club ID.
            key = c.execute(
                "SELECT 'league:'||f.id FROM fixtures f JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id WHERE f.competition='Brasileirão 2027' AND h.name='Mirassol' AND a.name='Vasco' AND f.status='scheduled' ORDER BY f.datetime_local LIMIT 1"
            ).fetchone()[0]
        advance(directory, before_fixture=key)
        with writer(directory) as (c, policy):
            write_json(
                directory / "mirassol_preview.json", fixture_preview(c, policy, key)
            )
    result = advance(directory, until="2027-12-31 23:59")
    with writer(directory) as (c, policy):
        result = audit(c, directory / "parent.sqlite")
        for key, (inputs, seeds, cached) in committed.items():
            row = c.execute(
                "SELECT * FROM world_executions WHERE fixture_key=?", (key,)
            ).fetchone()
            if (
                [row["input_sha256"], row["seed_json"]] != [inputs, seeds]
                or cached
                and row["result_sha256"] != cached
            ):
                raise ValueError("A resumed execution was rerolled")
        pending = c.execute(
            "SELECT key FROM world_fixtures WHERE status<>'final' AND home IS NOT NULL"
        ).fetchall()
        if (
            pending
            or c.execute("SELECT count(*) FROM world_champions").fetchone()[0] != 4
        ):
            raise ValueError("Incomplete season or missing champions")
        results = [
            dict(r)
            for r in c.execute(
                "SELECT key,competition,stage,kickoff,home,away,home_goals,away_goals,resolution_json FROM world_fixtures WHERE status='final' ORDER BY kickoff,key"
            )
        ]
        champions = [
            dict(r)
            for r in c.execute("SELECT * FROM world_champions ORDER BY competition")
        ]
        standings = [
            dict(r)
            for r in c.execute(
                "SELECT c.id,c.name,c.points,c.played,c.wins,c.draws,c.losses,c.gf,c.ga FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027 ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name"
            )
        ]
        payroll = [
            dict(r) for r in c.execute("SELECT * FROM payroll_periods ORDER BY period")
        ]
        states = [
            json.loads(r[0])
            for r in c.execute("SELECT state_json FROM world_player_state")
        ]
        report = {
            "scope": "NONCANONICAL DEVELOPMENT TEST",
            "seed": seed,
            "audit": result,
            "world_sha256": digest(fingerprints(c)),
            "resumption_preserved_commitments": len(committed),
            "results_private_spoilers": results,
            "champions_private_spoilers": champions,
            "standings_private_spoilers": standings,
            "payroll": payroll,
            "state_summary": {
                "forward_injuries": sum(s["injury_until"] is not None for s in states),
                "mean_stored_fitness": sum(s["fitness"] for s in states) / len(states),
            },
            "database_bytes": (directory / "database.sqlite").stat().st_size,
            "accepted_parent_sha256": file_sha256(parent),
        }
    write_json(directory / "private_season_report.json", report)
    if package:
        archive = directory.parent / (directory.name + ".zip")
        if not archive.exists():
            export_world(directory, archive)
        target = directory.parent / (directory.name + "-restored")
        if not target.exists():
            restored = restore_checkpoint(archive, target)
        else:
            from braga_era.checkpoints import verify_checkpoint

            restored = verify_checkpoint(target)
        report["package"] = {
            "sha256": file_sha256(archive),
            "bytes": archive.stat().st_size,
            "independently_restored": restored["independent_replay"],
        }
        write_json(directory / "private_season_report.json", report)
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k
                not in (
                    "results_private_spoilers",
                    "champions_private_spoilers",
                    "standings_private_spoilers",
                    "payroll",
                )
            }
        )
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", required=True)
    p.add_argument("--no-package", action="store_true")
    a = p.parse_args()
    run(a.db, a.output, a.seed, not a.no_package)
