# storage/schema.py
# Schema definitions and migration registry for SQLite tables.

from __future__ import annotations

import sqlite3
from collections.abc import Callable

_migrations: list[tuple[str, Callable[[sqlite3.Connection, str], None]]] = []


def register_migration(
    table_name: str,
    fn: Callable[[sqlite3.Connection, str], None],
) -> None:
    _migrations.append((table_name, fn))


def run_migrations(conn: sqlite3.Connection, schema_sql: str) -> None:
    for _table, fn in _migrations:
        fn(conn, schema_sql)


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

_KNOWLEDGE_SQL = """
    CREATE TABLE IF NOT EXISTS knowledge (
        key     TEXT PRIMARY KEY,
        value   TEXT NOT NULL,
        updated INTEGER NOT NULL
    );
"""

_APIKEYS_SQL = """
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

SCHEMA_SQL = f"{_HISTORY_SQL}\n{_KNOWLEDGE_SQL}\n{_APIKEYS_SQL}"


def _migrate_history(conn: sqlite3.Connection, _schema: str) -> None:
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


register_migration("history", _migrate_history)
