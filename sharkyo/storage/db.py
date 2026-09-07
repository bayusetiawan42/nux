# storage/db.py
# Centralized SQLite database connection and schema management.

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from sharkyo.core.constants import DB_FILE
from sharkyo.storage.schema import SCHEMA_SQL, run_migrations

_initialized_file: str | None = None


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    global _initialized_file
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    if _initialized_file != DB_FILE:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.executescript(SCHEMA_SQL)
        run_migrations(conn, SCHEMA_SQL)
        conn.commit()
        _initialized_file = DB_FILE
    try:
        yield conn
    finally:
        conn.close()
