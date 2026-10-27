"""Three production-style gates, simulated signers, TEST-ONLY authority only."""

import argparse
from contextlib import closing
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era import lineage
from braga_era.checkpoints import write_json
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.world.scope import calculation
from braga_era.world.storage import create
from braga_era.world.policy import ReadinessPolicy
from braga_era.world.runner import advance, InjectedCrash
from braga_era.world.packages import fingerprints

KEY = b"TEST-ONLY-TASK03D-SIMULATED-AUTHORITY-KEY"


def run(parent, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    registry = output / "authority" / "rehearsal.sqlite"
    if not registry.exists():
        lineage.provision(
            registry,
            KEY,
            test_only=True,
            commissioner="SIMULATED TEST COMMISSIONER",
            career_id="task03d-rehearsal-v1",
            seed="task03d-chain-fixed-v1",
        )
    moved = output / "machine-b"
    if (moved / "authority/career.sqlite").exists():
        registry = moved / "authority/career.sqlite"
    rows = []
    narrative = []
    source = Path(parent).resolve()
    for generation, until in enumerate(
        ["2027-09-30 23:59", "2027-10-03 23:59", "2027-10-06 23:59"], 1
    ):
        target = output / f"TEST-ONLY-checkpoint-{generation}"
        execution = f"task03d-batch-{generation}"
        with lineage.access(registry, KEY) as (c, trusted):
            existing = c.execute(
                "SELECT * FROM batches WHERE id=?", (execution,)
            ).fetchone()
        if not existing:
            manifest = lineage.prepare(
                registry, KEY, source, until=until, execution_id=execution
            )
            with lineage.access(registry, KEY) as (c, trusted):
                decision = lineage.expected_authorization(manifest, trusted)
            lineage.authorize(
                registry, KEY, source, manifest, decision, lineage.sign(KEY, decision)
            )
        if not existing or existing["state"] != "accepted":
            if generation == 2 and not (target / "world").exists():
                try:
                    lineage.execute(
                        registry, KEY, execution, target, crash="after_result"
                    )
                except InjectedCrash:
                    pass
            result = lineage.execute(registry, KEY, execution, target)
            decision = lineage.acceptance_template(registry, KEY, target)
            result = lineage.accept(
                registry, KEY, target, decision, lineage.sign(KEY, decision)
            )
        else:
            with lineage.access(registry, KEY) as (c, trusted):
                result = lineage.verify_payload(target / "payload", trusted, KEY)
        rows.append(result)
        source = target
        print(
            json.dumps(
                {
                    "generation": generation,
                    "new_receipts": result["new_receipts"],
                    "total_receipts": result["receipts"],
                    "checkpoint_sha256": result["checkpoint_sha256"],
                    "test_only": True,
                }
            ),
            flush=True,
        )
        first = "lib:LIB-R16-01:L1"
        page = lineage.gameplay(
            registry,
            KEY,
            "narrate",
            first,
            1,
            page_id=f"task03d-narration-{generation}",
        )
        repeated = lineage.gameplay(
            registry,
            KEY,
            "narrate",
            first,
            1,
            page_id=f"task03d-narration-{generation}",
        )
        if page != repeated or page["events"][0]["sequence"] != generation:
            raise ValueError("Narration retry or checkpoint transition lost its cursor")
        narrative.append(page["events"][0]["sequence"])
        if generation == 1:
            portable = output / "portable-after-batch-1"
            if not portable.exists():
                lineage.backup(registry, KEY, portable, transfer=True)
            if not moved.exists():
                lineage.restore_backup(portable, KEY, moved, expected_test_only=True)
            registry = moved / "authority/career.sqlite"
            source = moved / "accepted-head"
    with lineage.access(registry, KEY) as (c, trusted):
        seed = trusted["seed"]
        head = trusted["head"]
    continuous = output / "single-world-control"
    with calculation(True):
        if not continuous.exists():
            create(parent, continuous, seed, ReadinessPolicy())
        advance(continuous, until="2027-10-06 23:59")
    with connect_read_only(continuous / "database.sqlite") as a, connect_read_only(
        source / "payload/database.sqlite"
    ) as b:
        if fingerprints(a) != fingerprints(b):
            raise ValueError("Batch boundaries changed the logical football world")
        control = digest(fingerprints(a))
    report = {
        "scope": "TEST-ONLY NONCANONICAL CONTINUOUS CHECKPOINT REHEARSAL",
        "profile": lineage.PROFILE,
        "batches": rows,
        "accepted_test_head": head,
        "single_world_sha256": control,
        "batch_boundaries_change_football": False,
        "original_accepted_sha256": file_sha256(parent),
        "production_authority_provisioned": False,
        "official_matches_executed": 0,
        "narration_sequences_across_generations": narrative,
        "portable_machine_transfer_after_generation": 1,
        "registry": str(registry),
    }
    write_json(output / "rehearsal.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = run(a.db, a.output)
    print(
        json.dumps(
            {
                "ok": True,
                "head": r["accepted_test_head"],
                "single_world_sha256": r["single_world_sha256"],
            }
        )
    )
