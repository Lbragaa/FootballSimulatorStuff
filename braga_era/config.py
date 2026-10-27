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
    from .acceptance import catalog
    from .db import file_sha256

    root = Path(__file__).resolve().parents[1]
    for relative in (
        "output/accepted-046c/database.sqlite",
        "output/ci-accepted/database.sqlite",
        "output/Save046C_v2/database.sqlite",
    ):
        path = root / relative
        if path.is_file() and file_sha256(path) == catalog()["database_sha256"]:
            return path
    raise FileNotFoundError(
        "Accepted 046C v2 is not installed. Run python tools/bootstrap_accepted.py --download, or pass --db for explicit historical inspection. No silent fallback to old 046."
    )
