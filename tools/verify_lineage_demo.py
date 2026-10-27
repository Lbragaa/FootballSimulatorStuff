"""Compare portable logical evidence; physical SQLite/archive bytes may vary."""

import argparse
import json
from pathlib import Path


def verify(directory, reference):
    actual = json.loads((Path(directory) / "rehearsal.json").read_text())
    expected = json.loads(Path(reference).read_text())
    fields = (
        "profile",
        "single_world_sha256",
        "original_accepted_sha256",
        "batch_boundaries_change_football",
        "production_authority_provisioned",
        "official_matches_executed",
        "narration_sequences_across_generations",
        "portable_machine_transfer_after_generation",
    )
    for field in fields:
        if actual[field] != expected[field]:
            raise ValueError(f"Continuous rehearsal mismatch: {field}")
    previous = actual["original_accepted_sha256"]
    for index, (a, b) in enumerate(zip(actual["batches"], expected["batches"]), 1):
        for field in (
            "generation",
            "new_receipts",
            "receipts",
            "world_sha256",
            "test_only",
            "accepted",
            "independent_delta_replay",
        ):
            if a[field] != b[field]:
                raise ValueError(f"Batch {index} mismatch: {field}")
        if a["immediate_parent_sha256"] != previous or not a["validation"]["ok"]:
            raise ValueError("Broken accepted continuation")
        previous = a["checkpoint_sha256"]
    if len(actual["batches"]) != 3 or actual["accepted_test_head"] != previous:
        raise ValueError("Incomplete three-generation demonstration")
    return {
        "ok": True,
        "test_only": True,
        "single_world_sha256": actual["single_world_sha256"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--reference", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.directory, a.reference)))
