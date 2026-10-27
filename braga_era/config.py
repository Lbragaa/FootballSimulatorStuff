"""Portable path precedence: explicit CLI path, environment, repository default."""

import os
from pathlib import Path


def database_path(explicit: str | Path | None = None) -> Path:
    value = explicit or os.environ.get("BRAGA_ERA_DB")
    if value:
        return Path(value).expanduser().resolve()
    from .acceptance import registered_database

    accepted = registered_database()
    if accepted is not None:
        return accepted
    return (
        Path(__file__).resolve().parents[1] / "data/handoff/canonical/braga_save.sqlite"
    )
