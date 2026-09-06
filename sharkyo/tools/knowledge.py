"""Persistent user knowledge tool."""

from sharkyo.config import Config
from sharkyo.display import print_success
from sharkyo.knowledge import KnowledgeManager

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
            "required": ["op"],
        },
    },
}


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Execute knowledge operations."""
    op = args.get("op", "")
    key = args.get("key", "").strip()
    value = args.get("value", "").strip()
    km = KnowledgeManager()

    if op == "set":
        if not key or not value:
            return "Error: 'set' requires both key and value.", True
        km.set(key, value)
        print_success(f"Stored: [bold]{key}[/bold] = {value}")
        return f"Stored: {key} = {value}", True

    if op == "get":
        if not key:
            return "Error: 'get' requires a key.", True
        result = km.get(key)
        if result is None:
            return f"No knowledge found for key: {key}", True
        return f"{key} = {result}", True

    if op == "list":
        entries = km.list_all()
        if not entries:
            return "No knowledge stored yet.", True
        lines = [f"{k} = {v}" for k, v in entries]
        return "\n".join(lines), True

    if op == "delete":
        if not key:
            return "Error: 'delete' requires a key.", True
        deleted = km.delete(key)
        if deleted:
            print_success(f"Deleted knowledge key: {key}")
            return f"Deleted: {key}", True
        return f"Key not found: {key}", True

    return f"Unknown KNOWLEDGE op: {op}", True
