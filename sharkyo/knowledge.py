"""SQLite-backed persistent key/value facts about the user."""

import sqlite3
import time

from sharkyo.constants import DB_FILE


class KnowledgeManager:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL,
                updated INTEGER NOT NULL
            )
        """)
        self.conn.commit()

    def set(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO knowledge (key, value, updated) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
            (key.lower().strip(), value, int(time.time())),
        )
        self.conn.commit()

    def get(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM knowledge WHERE key = ?",
            (key.lower().strip(),),
        ).fetchone()
        return row[0] if row else None

    def list_all(self) -> list[tuple[str, str]]:
        return self.conn.execute(
            "SELECT key, value FROM knowledge ORDER BY updated DESC"
        ).fetchall()

    def delete(self, key: str) -> bool:
        """Delete a specific key. Returns True if it existed."""
        cur = self.conn.execute("DELETE FROM knowledge WHERE key = ?", (key.lower().strip(),))
        self.conn.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        self.conn.execute("DELETE FROM knowledge")
        self.conn.commit()
