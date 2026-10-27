"""Additive V2 structures. No change to V1 schema or its result identities."""

DDL = """
CREATE TABLE world_blobs(sha256 TEXT PRIMARY KEY, value_json TEXT NOT NULL);
CREATE TABLE world_draws(key TEXT PRIMARY KEY, competition TEXT NOT NULL, stage TEXT NOT NULL,
 commitment_json TEXT NOT NULL, status TEXT NOT NULL, pairings_json TEXT);
CREATE TABLE world_champions(competition TEXT PRIMARY KEY, club_key TEXT NOT NULL REFERENCES world_clubs(key),
 evidence_json TEXT NOT NULL);
"""
TABLES = {"world_draws", "world_champions"}


def enabled(c):
    return bool(
        c.execute("SELECT 1 FROM sqlite_master WHERE name='world_blobs'").fetchone()
    )


def pack(c, row):
    """Deduplicate complete row images; references commit exact canonical bytes."""
    from ..history import canonical_json, digest

    if row is None:
        return None
    result = {}
    for key, value in row.items():
        if isinstance(value, str) and len(value) > 512:
            sha = digest(value)
            c.execute(
                "INSERT OR IGNORE INTO world_blobs VALUES(?,?)",
                (sha, canonical_json(value)),
            )
            result[key] = {"$world_blob": sha}
        else:
            result[key] = value
    return result


def unpack(c, row):
    import json
    from ..history import digest

    if row is None:
        return None
    result = {}
    for key, value in row.items():
        if isinstance(value, dict) and set(value) == {"$world_blob"}:
            found = c.execute(
                "SELECT value_json FROM world_blobs WHERE sha256=?",
                (value["$world_blob"],),
            ).fetchone()
            if not found or digest(json.loads(found[0])) != value["$world_blob"]:
                raise ValueError("Missing or corrupted journal blob")
            result[key] = json.loads(found[0])
        else:
            result[key] = value
    return result
