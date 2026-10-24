"""Compare generated noncanonical demonstrations to reviewed regression artifacts."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.history import digest


def verify(directory, reference):
    actual = json.loads(
        (directory / "private_match_report.json").read_text(encoding="utf-8")
    )
    expected = json.loads(reference.read_text(encoding="utf-8"))
    for report in (actual, expected):
        if (
            report.get("official") is not False
            or report.get("scope") != "NONCANONICAL TEST SIMULATION"
        ):
            raise ValueError("Demonstrations must stay noncanonical")
        if not report["validation"]["ok"] or not report["database_guard"]["unchanged"]:
            raise ValueError("Demonstration failed validation or source protection")
        if digest(report["result"]) != report["result_sha256"]:
            raise ValueError("Result digest differs")
    if actual["result_sha256"] != expected["result_sha256"]:
        raise ValueError(
            "Deterministic regression differs; investigate model/runtime before revising evidence"
        )
    return actual["result_sha256"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    print(
        "PASS: deterministic noncanonical report "
        + verify(args.directory, args.reference)
    )
