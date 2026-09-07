# db.py
# Centralized SQLite database connection and schema management.

import sqlite3
from contextlib import contextmanager
from typing import Generator

from sharkyo.constants import DB_FILE


_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        role         TEXT    NOT NULL,
        content      TEXT,
        tool_calls   TEXT,
        tool_call_id TEXT,
        created_at   INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS knowledge (
        key     TEXT PRIMARY KEY,
        value   TEXT NOT NULL,
        updated INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS apikeys (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        key      TEXT    NOT NULL UNIQUE,
        provider TEXT    NOT NULL DEFAULT 'groq',
        base_url TEXT,
        active   INTEGER NOT NULL DEFAULT 0,
        reset_at INTEGER NOT NULL DEFAULT 0
    );
"""


def _init_schema(conn: sqlite3.Connection) -> None:
    # Enable WAL mode and create all required tables if they do not exist.
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.executescript(_SCHEMA_SQL)
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
