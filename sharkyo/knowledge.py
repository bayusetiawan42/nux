# knowledge.py
# Persistent key/value knowledge store for user facts.

import time

from sharkyo.db import get_connection


class KnowledgeManager:
    # Manages persistent key/value facts remembered about the user.
    # Each public method opens and closes its own DB connection.

    def set(self, key: str, value: str) -> None:
        # Store or update a key-value fact.
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO knowledge (key, value, updated) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated""",
                (key.lower().strip(), value.strip(), int(time.time())),
            )
            conn.commit()

    def get(self, key: str) -> str | None:
        # Retrieve a specific fact by key.
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM knowledge WHERE key = ?",
                (key.lower().strip(),),
            ).fetchone()
        return row["value"] if row else None

    def list_all(self) -> list[tuple[str, str]]:
        # List all stored facts ordered by last updated.
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT key, value FROM knowledge ORDER BY updated DESC"
            ).fetchall()
        return [(r["key"], r["value"]) for r in rows]

    def delete(self, key: str) -> bool:
        # Delete a fact by key. Returns True if deleted, False if not found.
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM knowledge WHERE key = ?",
                (key.lower().strip(),),
            )
            conn.commit()
            return cur.rowcount > 0

    def clear(self) -> None:
        # Wipe all stored knowledge.
        with get_connection() as conn:
            conn.execute("DELETE FROM knowledge")
            conn.commit()
