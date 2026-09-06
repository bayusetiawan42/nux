"""SQLite-backed chat history with session isolation."""

import json
import sqlite3
import uuid
import time

from sharkyo.constants import DB_FILE

_DEFAULT_MAX = 20


class HistoryManager:
    def __init__(self, max_messages: int = _DEFAULT_MAX) -> None:
        self.max_messages = max_messages
        self.session_id = str(uuid.uuid4())
        self.conn = sqlite3.connect(DB_FILE)
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                role         TEXT    NOT NULL,
                content      TEXT,
                tool_calls   TEXT,
                tool_call_id TEXT,
                created_at   INTEGER NOT NULL
            );
        """)
        self.conn.commit()

    def load(self) -> list[dict]:
        """Return last max_messages rows as clean API-ready dicts."""
        rows = self.conn.execute(
            """SELECT role, content, tool_calls, tool_call_id
               FROM history
               ORDER BY id DESC
               LIMIT ?""",
            (self.max_messages,),
        ).fetchall()
        msgs = []
        for role, content, tool_calls_json, tool_call_id in reversed(rows):
            msg: dict = {"role": role}
            if content is not None:
                msg["content"] = content
            if tool_calls_json:
                msg["tool_calls"] = json.loads(tool_calls_json)
            if tool_call_id:
                msg["tool_call_id"] = tool_call_id
            msgs.append(msg)
        return msgs

    def append_user(self, content: str) -> None:
        self._insert(role="user", content=content)

    def append_assistant(self, content: str | None, tool_calls: list | None = None) -> None:
        """Save assistant message. tool_calls must be clean dicts, NOT pydantic objects."""
        tc_json = None
        if tool_calls:
            # sanitize — only keep fields the API needs
            clean = []
            for tc in tool_calls:
                if hasattr(tc, "model_dump"):
                    tc = tc.model_dump()
                clean.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                })
            # Only save if all tool_calls have a name (safety check)
            if all(c["function"]["name"] for c in clean):
                tc_json = json.dumps(clean)
        self._insert(role="assistant", content=content, tool_calls=tc_json)

    def append_tool_result(self, tool_call_id: str, content: str) -> None:
        self._insert(role="tool", content=content, tool_call_id=tool_call_id)

    def _insert(self, role: str, content: str | None = None,
                tool_calls: str | None = None, tool_call_id: str | None = None) -> None:
        self.conn.execute(
            """INSERT INTO history (session_id, role, content, tool_calls, tool_call_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.session_id, role, content, tool_calls, tool_call_id, int(time.time())),
        )
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM history")
        self.conn.commit()
