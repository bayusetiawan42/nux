# storage/history.py
# SQLite-backed chat history management.

import json
import time

from sharkyo.storage.db import get_connection

_DEFAULT_MAX = 12


class HistoryManager:
    def __init__(self, max_messages: int = _DEFAULT_MAX) -> None:
        self.max_messages = max_messages

    def load(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT role, content, tool_calls, tool_call_id
                   FROM history
                   ORDER BY id DESC
                   LIMIT ?""",
                (self.max_messages,),
            ).fetchall()

        msgs: list[dict] = []
        for row in reversed(rows):
            msg: dict = {"role": row["role"]}
            if row["content"] is not None:
                msg["content"] = row["content"]
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            msgs.append(msg)

        while msgs and msgs[0]["role"] == "tool":
            msgs.pop(0)
        return msgs

    def append_user(self, content: str) -> None:
        self._insert(role="user", content=content)

    def append_assistant(
        self,
        content: str | None,
        tool_calls: list | None = None,
    ) -> None:
        tc_json: str | None = None
        if tool_calls:
            clean = []
            for tc in tool_calls:
                if hasattr(tc, "model_dump"):
                    tc = tc.model_dump()
                clean.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                )
            if all(c["function"]["name"] for c in clean):
                tc_json = json.dumps(clean)

        if content is None and not tc_json:
            return

        self._insert(role="assistant", content=content, tool_calls=tc_json)

    def append_tool_result(self, tool_call_id: str, content: str) -> None:
        self._insert(role="tool", content=content, tool_call_id=tool_call_id)

    def _insert(
        self,
        role: str,
        content: str | None = None,
        tool_calls: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO history (role, content, tool_calls, tool_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (role, content, tool_calls, tool_call_id, int(time.time())),
            )
            conn.commit()

    def clear(self) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM history")
            conn.commit()
