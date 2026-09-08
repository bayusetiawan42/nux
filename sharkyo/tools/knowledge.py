# tools/knowledge.py
# Persistent user knowledge tool.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sharkyo.core.config import Config
from sharkyo.storage.knowledge import KnowledgeManager
from sharkyo.tools import register_tool
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import print_success

if TYPE_CHECKING:
    from sharkyo.server.protocol import Packet

SCHEMA = {
    "type": "function",
    "function": {
        "name": "KNOWLEDGE",
        "description": (
            "Persist or retrieve facts about the user across sessions. "
            "Use 'set' to store a key-value fact. "
            "Use 'get' to retrieve a specific key. "
            "Use 'list' to dump all stored knowledge. "
            "Use 'delete' to remove a specific key."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["set", "get", "list", "delete"],
                    "description": "Operation: set, get, list, or delete.",
                },
                "key": {
                    "type": "string",
                    "description": "The knowledge key (required for set, get, delete).",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store (required for set).",
                },
            },
            "required": ["op", "key"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class KnowledgeArgs:
    op: str
    key: str = ""
    value: str = ""

    @classmethod
    def from_dict(cls, args: dict) -> KnowledgeArgs:
        return cls(
            op=args.get("op", ""),
            key=args.get("key", "").strip(),
            value=args.get("value", "").strip(),
        )


def list_all_formatted() -> str:
    entries = KnowledgeManager().list_all()
    if not entries:
        return ""
    return "\n".join(f"{k} = {v}" for k, v in entries)


def delete_key(key: str) -> tuple[bool, str]:
    deleted = KnowledgeManager().delete(key)
    if deleted:
        print_success(f"Deleted knowledge key: {key}")
        return True, f"Deleted: {key}"
    return False, f"Key not found: {key}"


def clear_all() -> str:
    KnowledgeManager().clear()
    print_success("All knowledge cleared.")
    return "All knowledge cleared."


@register_tool("KNOWLEDGE")
def execute(args: dict, config: Config | None, packet: Packet) -> ToolResult:
    parsed = KnowledgeArgs.from_dict(args)
    km = KnowledgeManager()

    if parsed.op == "set":
        if not parsed.key or not parsed.value:
            return ToolResult(
                output="Error: 'set' requires both key and value.", should_continue=True
            )
        km.set(parsed.key, parsed.value)
        print_success(f"Stored: [bold]{parsed.key}[/bold] = {parsed.value}")
        return ToolResult(output=f"Stored: {parsed.key} = {parsed.value}", should_continue=True)

    if parsed.op == "get":
        if not parsed.key:
            return ToolResult(output="Error: 'get' requires a key.", should_continue=True)
        result = km.get(parsed.key)
        if result is None:
            return ToolResult(
                output=f"No knowledge found for key: {parsed.key}", should_continue=True
            )
        return ToolResult(output=f"{parsed.key} = {result}", should_continue=True)

    if parsed.op == "list":
        formatted = list_all_formatted()
        if not formatted:
            return ToolResult(output="No knowledge stored yet.", should_continue=True)
        return ToolResult(output=formatted, should_continue=True)

    if parsed.op == "delete":
        if not parsed.key:
            return ToolResult(output="Error: 'delete' requires a key.", should_continue=True)
        _, msg = delete_key(parsed.key)
        return ToolResult(output=msg, should_continue=True)

    return ToolResult(output=f"Unknown KNOWLEDGE op: {parsed.op}", should_continue=True)
