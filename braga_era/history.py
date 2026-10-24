"""Stable logical fingerprints independent of SQLite page layout."""
import hashlib
from importlib.resources import files
import json


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_fingerprint(connection, name: str) -> dict:
    cursor = connection.execute(f"SELECT * FROM {quote_identifier(name)}")
    columns = [column[0] for column in cursor.description]
    # Sort serialized rows: handles NULLs and tables without primary keys.
    rows = sorted(canonical_json(list(row)) for row in cursor)
    return {"rows": len(rows), "sha256": digest({"columns": columns, "rows": rows})}


def completed_fixtures(connection) -> list[dict]:
    return [dict(row) for row in connection.execute(
        "SELECT * FROM fixtures WHERE status='final' ORDER BY id")]


def load_baseline() -> dict:
    return json.loads(files("braga_era").joinpath("baselines/save046.json").read_text(encoding="utf-8"))
