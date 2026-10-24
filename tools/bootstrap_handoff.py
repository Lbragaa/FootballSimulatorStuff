"""Reproduce the unmodified handoff locally, with hash and path validation."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = "527dd4d8d62f3bca8d4e0459a137e8588558315aed19aabc0cda58edbe007719"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive: Path, destination: Path) -> None:
    if sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("Original handoff ZIP checksum does not match Save 046")
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        paths = []
        seen = set()
        for info in members:
            name = PurePosixPath(info.filename)
            # zipfile normalizes Windows separators when reading; inspect the
            # original name as well so malformed raw paths are not concealed.
            if (name.is_absolute() or ".." in name.parts or "\\" in info.orig_filename
                    or "\x00" in info.orig_filename
                    or ":" in info.filename or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError(f"Unsafe archive member: {info.filename}")
            target = destination.joinpath(*name.parts).resolve()
            if not target.is_relative_to(destination) or str(target).casefold() in seen:
                raise ValueError(f"Unsafe or duplicate archive path: {info.filename}")
            seen.add(str(target).casefold())
            paths.append((info, target))
        if sum(i.file_size for i in members) > 100_000_000:
            raise ValueError("Unexpected handoff size")
        # Validate the entire payload and manifest before writing any files.
        payload = {i.filename: bundle.read(i) for i in members if not i.is_dir()}
        manifest = payload["MANIFEST_SHA256.txt"].decode("utf-8")
        listed = set()
        for line in manifest.splitlines():
            if not line.strip():
                continue
            expected, name = line.split("  ", 1)
            if hashlib.sha256(payload[name]).hexdigest() != expected:
                raise ValueError(f"Manifest mismatch: {name}")
            listed.add(name)
        if listed != set(payload) - {"MANIFEST_SHA256.txt"}:
            raise ValueError("Manifest does not cover the complete archive")
        for info, target in paths:
            if target.exists() and (target.is_dir() != info.is_dir() or
                    (not info.is_dir() and target.read_bytes() != payload[info.filename])):
                raise ValueError(f"Refusing to overwrite changed handoff file: {target}")
        for info, target in paths:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(payload[info.filename])
                try:
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "BRAGA_ERA_HANDOFF_AFTER_046.zip")
    parser.add_argument("--destination", type=Path, default=ROOT / "data/handoff")
    args = parser.parse_args()
    extract(args.archive, args.destination)
    print(f"Verified handoff extracted to {args.destination.resolve()}")
    print(f"ZIP SHA256: {sha256(args.archive)}")
    print(f"Database SHA256: {sha256(args.destination / 'canonical/braga_save.sqlite')}")


if __name__ == "__main__":
    main()
