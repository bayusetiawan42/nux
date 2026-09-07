# db.py
# Centralized SQLite database connection and schema management.
#
# TODO: Future plan — replace open/close-per-call with a persistent connection server.
# Currently each operation opens and closes its own connection (safe, simple).
# The planned architecture: a lightweight background server process that initializes
# the DB once and handles requests via IPC (e.g. Unix socket or named pipe),
# eliminating per-invocation connection overhead for faster sharkyo startup times.

import sqlite3
from contextlib import contextmanager
from typing import Generator

from sharkyo.constants import DB_FILE


_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   TEXT    NOT NULL,
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
    # Create all required tables if they do not exist.
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    # Context manager: opens, yields, and closes a WAL-mode SQLite connection.
    # Schema is initialized on every open (idempotent via IF NOT EXISTS).
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    _init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()
