"""Install the exact accepted ZIP into a fresh directory; no promotion/simulation."""

from __future__ import annotations
import argparse
from pathlib import Path
import sys
import tempfile
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from braga_era.acceptance import catalog
from braga_era.checkpoints import restore_checkpoint
from braga_era.db import file_sha256


def install(archive: Path, output: Path):
    approved = catalog()
    if file_sha256(archive) != approved["package_sha256"]:
        raise ValueError(
            "STOP: package differs from approved ZIP SHA256; do not rewrite expected values"
        )
    result = restore_checkpoint(archive, output)
    if file_sha256(output / "database.sqlite") != approved["database_sha256"]:
        raise ValueError("STOP: restored DB differs from exact approved artifact")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("output/accepted-046c"))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh install directory")
    if args.download:
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output.resolve().parent) as scratch:
            archive = Path(scratch) / "accepted.zip"
            request = urllib.request.Request(
                catalog()["download_url"],
                headers={"User-Agent": "braga-era-accepted-bootstrap"},
            )
            with urllib.request.urlopen(request, timeout=60) as response, archive.open(
                "wb"
            ) as stream:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 100_000_000:
                        raise ValueError("Unexpected package size")
                    stream.write(chunk)
            install(archive, args.output)
    else:
        install(args.archive, args.output)
    print(
        f"Accepted artifact verified/restored to {args.output.resolve()}; no match executed or registry changed"
    )


if __name__ == "__main__":
    main()
