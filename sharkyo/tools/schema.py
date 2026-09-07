# tools/schema.py
# Pure data: OpenAI function-calling schema for all tools.
# No tool module imports — just dicts.

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "CMD",
            "description": (
                "Run a shell command on the user's machine. Output streams to the "
                "user's terminal live as it happens. "
                "Use review_output=true if you need to see the output (stdout+stderr "
                "merged, capped to the last few KB) to give a follow-up reply. "
                "Use review_output_stderr=true if you only need to know whether the "
                "command failed; the transcript is then sent back only when the exit "
                "code is non-zero. Leave both false if you don't need to see the output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "review_output": {
                        "type": "boolean",
                        "description": (
                            "Send the final tail of stdout+stderr back to you for a "
                            "follow-up reply. Default: false."
                        ),
                    },
                    "review_output_stderr": {
                        "type": "boolean",
                        "description": (
                            "Send the transcript back to you only when the command "
                            "fails (non-zero exit code). Useful for checking if a "
                            "command produced errors. Default: false."
                        ),
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
    {
        "type": "function",
        "function": {
            "name": "SKILL",
            "description": (
                "Search internal skills and guides for best practices or instructions on "
                "handling specialized tasks (such as 'reminder', 'timer', 'alarm', etc.). "
                "Call this when the user asks for a feature or task you need instructions to perform."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords describing the required skill or task (e.g. 'reminder', 'timer').",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "QUESTIONARY",
            "description": (
                "Ask the user one or more interactive questions to clarify their needs before acting. "
                "Use this when you need to gather requirements, preferences, or choices from the user "
                "before running a command or making a decision. "
                "Questions can be free-text, yes/no, single-choice, or multiple-choice. "
                "Returns all answers so you can proceed with full context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intro": {
                        "type": "string",
                        "description": "Optional short message shown before the questions.",
                    },
                    "questions": {
                        "type": "array",
                        "description": "List of questions to ask the user.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "Short identifier for this answer (e.g. 'project_name').",
                                },
                                "type": {
                                    "type": "string",
                                    "enum": ["text", "confirm", "select", "checkbox"],
                                    "description": (
                                        "Question type: "
                                        "'text' = free-form input, "
                                        "'confirm' = yes/no, "
                                        "'select' = pick one from choices, "
                                        "'checkbox' = pick multiple from choices."
                                    ),
                                },
                                "message": {
                                    "type": "string",
                                    "description": "The question text shown to the user.",
                                },
                                "choices": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Options for 'select' or 'checkbox' types.",
                                },
                                "default": {
                                    "type": "string",
                                    "description": "Optional default value (for 'text' and 'select' types).",
                                },
                            },
                            "required": ["key", "type", "message"],
                        },
                    },
                },
                "required": ["questions"],
            },
        },
    },
]
