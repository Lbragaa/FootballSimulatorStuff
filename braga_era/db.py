"""Read-only SQLite connections, even for arbitrary user-supplied files."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
from typing import Iterator


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read_only_authorizer(action, arg1, arg2, database, trigger):
    # Allow only SELECT and reading PRAGMAs needed by this application. In
    # particular, deny ATTACH and disabling query_only, not just ordinary DML.
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
               sqlite3.SQLITE_RECURSIVE}
    if action in allowed:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg1.lower() in {
        "integrity_check", "foreign_key_check", "table_info", "query_only",
    } and (arg2 is None or arg1.lower() == "table_info"):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


@contextmanager
def connect_read_only(path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}. Run python tools/bootstrap_handoff.py "
                                "or pass --db PATH / set BRAGA_ERA_DB.")
    # as_uri escapes spaces, #, ? and Windows drive paths correctly. Do not use
    # immutable=1: that could ignore an unexpected live WAL on a supplied copy.
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.enable_load_extension(False)
        connection.execute("PRAGMA query_only=ON")
        connection.set_authorizer(_read_only_authorizer)
        yield connection
    finally:
        connection.close()
