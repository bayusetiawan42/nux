"""SQLite-backed chat history management with session isolation."""

import json
import time
import uuid
from sharkyo.db import get_connection

_DEFAULT_MAX = 12


class HistoryManager:
    """Manages chat messages stored in SQLite, formatted for OpenAI-compatible APIs."""

    def __init__(self, max_messages: int = _DEFAULT_MAX) -> None:
        self.max_messages = max_messages
        self.session_id = str(uuid.uuid4())
        self.conn = get_connection()

    def load(self) -> list[dict]:
        """Return the most recent messages formatted as clean API message dictionaries."""
        rows = self.conn.execute(
            """SELECT role, content, tool_calls, tool_call_id
               FROM history
               ORDER BY id DESC
               LIMIT ?""",
            (self.max_messages,),
        ).fetchall()

        msgs = []
        for row in reversed(rows):
            msg: dict = {"role": row["role"]}
            if row["content"] is not None:
                msg["content"] = row["content"]
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            msgs.append(msg)
        return msgs

    def append_user(self, content: str) -> None:
        """Record a user message."""
        self._insert(role="user", content=content)

    def append_assistant(self, content: str | None, tool_calls: list | None = None) -> None:
        """Record an assistant message. Safely sanitizes tool_calls."""
        tc_json = None
        if tool_calls:
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
                    },
                })
            # Only save if all tool calls have a valid function name
            if all(c["function"]["name"] for c in clean):
                tc_json = json.dumps(clean)

        # Do not save completely empty assistant records
        if content is None and not tc_json:
            return

        self._insert(role="assistant", content=content, tool_calls=tc_json)

    def append_tool_result(self, tool_call_id: str, content: str) -> None:
        """Record a tool result message."""
        self._insert(role="tool", content=content, tool_call_id=tool_call_id)

    def _insert(
        self,
        role: str,
        content: str | None = None,
        tool_calls: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO history (session_id, role, content, tool_calls, tool_call_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.session_id, role, content, tool_calls, tool_call_id, int(time.time())),
        )
        self.conn.commit()

    def clear(self) -> None:
        """Clear all stored chat history."""
        self.conn.execute("DELETE FROM history")
        self.conn.commit()
