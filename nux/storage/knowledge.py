# storage/knowledge.py
# Persistent key/value knowledge store for user facts.

import time

from nux.storage.db import (
    execute_read,
    execute_read_one,
    execute_write,
    execute_write_returning,
)


class KnowledgeManager:
    def set(self, key: str, value: str) -> None:
        execute_write(
            """INSERT INTO knowledge (key, value, updated) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated""",
            (key.lower().strip(), value.strip(), int(time.time())),
        )

    def get(self, key: str) -> str | None:
        row = execute_read_one(
            "SELECT value FROM knowledge WHERE key = ?",
            (key.lower().strip(),),
        )
        return row["value"] if row else None

    def list_all(self) -> list[tuple[str, str]]:
        rows = execute_read("SELECT key, value FROM knowledge ORDER BY updated DESC")
        return [(r["key"], r["value"]) for r in rows]

    def delete(self, key: str) -> bool:
        cur = execute_write_returning(
            "DELETE FROM knowledge WHERE key = ?",
            (key.lower().strip(),),
        )
        return cur.rowcount > 0

    def clear(self) -> None:
        execute_write("DELETE FROM knowledge")
