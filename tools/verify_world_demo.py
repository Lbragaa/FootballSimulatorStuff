"""Cross-platform logical regression check; never reveals a future Vasco score."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.acceptance import catalog
from braga_era.db import connect_read_only, file_sha256
from braga_era.world.storage import logical_hash


def verify(directory, reference):
    proof = json.loads((directory / "demonstration.json").read_text(encoding="utf-8"))
    expected = json.loads(reference.read_text(encoding="utf-8"))
    if proof["scope"] != "NONCANONICAL DEVELOPMENT TEST" or proof["promotable"]:
        raise ValueError("Development scope mismatch")
    if (
        proof["parent_sha256_before"] != proof["parent_sha256_after"]
        or proof["parent_sha256_after"] != catalog()["database_sha256"]
    ):
        raise ValueError("Accepted source changed")
    if (proof["continental_matches"], proof["league_matches"]) != (16, 10):
        raise ValueError("Demonstration omitted fixtures")
    if (
        not proof["independent_restoration_and_replay"]
        or proof["resumption_changed_results"]
    ):
        raise ValueError("Restoration/resumption proof failed")
    if proof["world_sha256"] != expected["world_sha256"]:
        raise ValueError(
            "Logical world regression differs; investigate runtime/model before changing reviewed evidence"
        )
    if proof["archive_sha256"] != file_sha256(directory / "NONCANONICAL_DEV_03B.zip"):
        raise ValueError("Archive hash differs from proof")
    for folder in ("world", "independent_restore"):
        with connect_read_only(directory / folder / "database.sqlite") as c:
            if logical_hash(c) != proof["world_sha256"]:
                raise ValueError("Restored/working football world differs")
    return proof["world_sha256"]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    args = p.parse_args()
    print("PASS: NONCANONICAL logical world " + verify(args.directory, args.reference))
