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

# Tracks which DB file has already been schema-initialized in this process.
# Schema creation and legacy migration are idempotent, so on the daemon the
# work happens a single time at startup, and after a fork the child inherits
# the value and skips it entirely (its DB is already warm). Keyed by file path
# so switching databases (e.g. in tests) re-initializes the new one.
_initialized_file: str | None = None


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
    # Schema/migration work is done once per DB file and skipped afterwards.
    global _initialized_file
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    if _initialized_file != DB_FILE:
        _init_schema(conn)
        _initialized_file = DB_FILE
    try:
        yield conn
    finally:
        conn.close()