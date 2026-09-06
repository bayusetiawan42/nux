"""Centralized SQLite database connection and schema management."""

import sqlite3
from sharkyo.constants import DB_FILE


def get_connection() -> sqlite3.Connection:
    """Return an initialized SQLite connection with WAL mode and Row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all required tables if they do not exist."""
    conn.executescript("""
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
    """)
    conn.commit()
