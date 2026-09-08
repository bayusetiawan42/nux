# tools/knowledge.py
# Persistent user knowledge tool.

from dataclasses import dataclass

from sharkyo.core.config import Config
from sharkyo.storage.knowledge import KnowledgeManager
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import print_success

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
    def from_dict(cls, args: dict) -> "KnowledgeArgs":
        return cls(
            op=args.get("op", ""),
            key=args.get("key", "").strip(),
            value=args.get("value", "").strip(),
        )


def execute(args: dict, config: Config | None = None) -> ToolResult:
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
        entries = km.list_all()
        if not entries:
            return ToolResult(output="No knowledge stored yet.", should_continue=True)
        lines = [f"{k} = {v}" for k, v in entries]
        return ToolResult(output="\n".join(lines), should_continue=True)

    if parsed.op == "delete":
        if not parsed.key:
            return ToolResult(output="Error: 'delete' requires a key.", should_continue=True)
        deleted = km.delete(parsed.key)
        if deleted:
            print_success(f"Deleted knowledge key: {parsed.key}")
            return ToolResult(output=f"Deleted: {parsed.key}", should_continue=True)
        return ToolResult(output=f"Key not found: {parsed.key}", should_continue=True)

    return ToolResult(output=f"Unknown KNOWLEDGE op: {parsed.op}", should_continue=True)
