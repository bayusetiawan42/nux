# db.py
# Centralized SQLite database connection and schema management.

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from sharkyo.constants import DB_FILE

_HISTORY_SQL = """
    CREATE TABLE IF NOT EXISTS history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        role         TEXT    NOT NULL,
        content      TEXT,
        tool_calls   TEXT,
        tool_call_id TEXT,
        created_at   INTEGER NOT NULL
    );
"""

_SCHEMA_SQL = f"""
    {_HISTORY_SQL}

    CREATE TABLE IF NOT EXISTS knowledge (
        key     TEXT PRIMARY KEY,
        value   TEXT NOT NULL,
        updated INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS apikeys (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        key_ref  TEXT    NOT NULL UNIQUE,
        provider TEXT    NOT NULL DEFAULT 'groq',
        base_url TEXT,
        active   INTEGER NOT NULL DEFAULT 0,
        reset_at INTEGER NOT NULL DEFAULT 0,
        storage  TEXT    NOT NULL DEFAULT 'keyring'
    );
"""


def _migrate_history(conn: sqlite3.Connection) -> None:
    # Rebuild the legacy history table (which had a NOT NULL session_id column)
    # into the schema below, preserving existing rows.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(history)")]
    if "session_id" not in cols:
        return
    conn.execute("ALTER TABLE history RENAME TO history_legacy")
    conn.executescript(_HISTORY_SQL)
    shared = [c for c in ("id", "role", "content", "tool_calls", "tool_call_id", "created_at") if c in cols]
    conn.execute(
        f"INSERT INTO history ({', '.join(shared)}) "
        f"SELECT {', '.join(shared)} FROM history_legacy"
    )
    conn.execute("DROP TABLE history_legacy")
    conn.commit()


def _init_schema(conn: sqlite3.Connection) -> None:
    # Enable WAL mode, create all required tables, and migrate legacy layouts.
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.executescript(_SCHEMA_SQL)
    # Lazy import to avoid a circular import (apikeys imports get_connection).
    from sharkyo.apikeys import migrate_legacy

    migrate_legacy(conn, _SCHEMA_SQL)
    _migrate_history(conn)
    conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    # Context manager: opens, yields, and closes a SQLite connection.
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()