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


def execute_write(sql: str, params: tuple = ()) -> None:
    with get_connection() as conn:
        conn.execute(sql, params)
        conn.commit()


def execute_write_returning(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def execute_read(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def execute_read_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(sql, params).fetchone()
