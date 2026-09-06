"""Tool schemas exposed to the LLM."""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "CMD",
            "description": "Run a shell command on the user's machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "see_output": {
                        "type": "boolean",
                        "description": "Send command output back for a follow-up reply. Default: false.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
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
    },
]
