"""Check spoiler-free full-season regression identity across Python/platforms."""

import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
p.add_argument("--reference", type=Path, required=True)
a = p.parse_args()
actual = json.loads(
    (a.directory / "private_season_report.json").read_text(encoding="utf-8")
)
expected = json.loads(a.reference.read_text(encoding="utf-8"))
for key in ("scope", "seed", "world_sha256", "accepted_parent_sha256"):
    if actual[key] != expected[key]:
        raise SystemExit("Season regression mismatch: " + key)
for key in ("receipts", "league_final", "continental_final", "rest_exceptions"):
    if actual["audit"][key] != expected["audit"][key]:
        raise SystemExit("Season audit mismatch: " + key)
if not actual["audit"]["ok"] or len(actual["champions_private_spoilers"]) != 4:
    raise SystemExit("Incomplete season")
print(
    json.dumps(
        {
            "ok": True,
            "scope": actual["scope"],
            "world_sha256": actual["world_sha256"],
            "receipts": actual["audit"]["receipts"],
        }
    )
)
