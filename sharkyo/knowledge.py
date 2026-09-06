"""Persistent key/value knowledge store for user facts."""

import time
from sharkyo.db import get_connection


class KnowledgeManager:
    """Manages persistent key/value facts remembered about the user."""

    def __init__(self) -> None:
        self.conn = get_connection()

    def set(self, key: str, value: str) -> None:
        """Store or update a key-value fact."""
        self.conn.execute(
            """INSERT INTO knowledge (key, value, updated) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated""",
            (key.lower().strip(), value.strip(), int(time.time())),
        )
        self.conn.commit()

    def get(self, key: str) -> str | None:
        """Retrieve a specific fact by key."""
        row = self.conn.execute(
            "SELECT value FROM knowledge WHERE key = ?",
            (key.lower().strip(),),
        ).fetchone()
        return row["value"] if row else None

    def list_all(self) -> list[tuple[str, str]]:
        """List all stored facts ordered by last updated."""
        rows = self.conn.execute(
            "SELECT key, value FROM knowledge ORDER BY updated DESC"
        ).fetchall()
        return [(r["key"], r["value"]) for r in rows]

    def delete(self, key: str) -> bool:
        """Delete a fact by key. Returns True if deleted, False if not found."""
        cur = self.conn.execute(
            "DELETE FROM knowledge WHERE key = ?",
            (key.lower().strip(),),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        """Wipe all stored knowledge."""
        self.conn.execute("DELETE FROM knowledge")
        self.conn.commit()
