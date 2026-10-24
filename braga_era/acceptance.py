"""Resolve an approved administrative checkpoint; never grant match execution."""

from importlib.resources import files
import json
import os
from pathlib import Path

from .db import file_sha256


def catalog():
    return json.loads(
        files("braga_era")
        .joinpath("baselines/accepted046c.json")
        .read_text(encoding="utf-8")
    )


def registry_path():
    return (
        Path(
            os.environ.get(
                "BRAGA_ERA_REGISTRY",
                Path(__file__).resolve().parents[1] / "output/canonical.json",
            )
        )
        .expanduser()
        .resolve()
    )


def registered_database():
    path = registry_path()
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    approved = catalog()
    if (
        record.get("registry_format") != 1
        or record.get("save_version") != approved["save_version"]
        or record.get("database_sha256") != approved["database_sha256"]
        or record.get("parent_sha256") != approved["parent_sha256"]
    ):
        raise ValueError(
            "Accepted registry differs from commissioner-approved checkpoint"
        )
    database = (
        path.parent / record["checkpoint_directory"] / "database.sqlite"
    ).resolve()
    if not database.is_file() or file_sha256(database) != approved["database_sha256"]:
        raise ValueError(
            "Accepted checkpoint missing or bytes changed; restore exact approved artifact"
        )
    return database


def accepted_context(path):
    approved = catalog()
    if file_sha256(Path(path)) != approved["database_sha256"]:
        return None
    return {
        "status": "accepted_administrative_checkpoint",
        "save_version": "046C",
        "proposal_revision": "v2",
        "authority": approved["authority"],
        "database_sha256": approved["database_sha256"],
        "official_match_execution_authorized": False,
    }
