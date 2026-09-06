"""Interactive questionary tool — ask the user structured questions."""

import questionary as q

from sharkyo.config import Config
from sharkyo.display import console, print_info

SCHEMA = {
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
                    "description": "Optional short message shown before the questions (e.g. 'Let me ask a few things first.').",
                },
                "questions": {
                    "type": "array",
                    "description": "List of questions to ask the user.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Short identifier for this answer (e.g. 'project_name', 'use_docker').",
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
}

_STYLE = q.Style([
    ("qmark",       "fg:#00bcd4 bold"),
    ("question",    "bold"),
    ("pointer",     "fg:#00bcd4 bold"),
    ("highlighted", "fg:#00bcd4 bold"),
    ("selected",    "fg:#00bcd4"),
    ("answer",      "fg:#00bcd4 bold"),
])


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Spawn interactive questions and return answers to the model."""
    intro = args.get("intro", "").strip()
    questions = args.get("questions", [])

    if not questions:
        return "Error: 'questions' list is empty.", True

    if intro:
        console.print(f"\n  [bold cyan]?[/bold cyan] {intro}\n")
    else:
        console.print()

    answers: dict[str, object] = {}

    for spec in questions:
        key     = spec.get("key", "answer")
        qtype   = spec.get("type", "text")
        message = spec.get("message", "")
        choices = spec.get("choices", [])
        default = spec.get("default")

        try:
            if qtype == "text":
                kwargs = {"style": _STYLE}
                if default:
                    kwargs["default"] = default
                answer = q.text(message, **kwargs).ask()

            elif qtype == "confirm":
                default_bool = str(default).lower() in ("true", "yes", "1") if default else False
                answer = q.confirm(message, default=default_bool, style=_STYLE).ask()

            elif qtype == "select":
                if not choices:
                    answers[key] = None
                    continue
                kwargs = {"style": _STYLE}
                if default and default in choices:
                    kwargs["default"] = default
                answer = q.select(message, choices=choices, **kwargs).ask()

            elif qtype == "checkbox":
                if not choices:
                    answers[key] = []
                    continue
                answer = q.checkbox(message, choices=choices, style=_STYLE).ask()

            else:
                answer = q.text(message, style=_STYLE).ask()

            # User hit Ctrl-C
            if answer is None:
                print_info("Questionary cancelled.")
                return "User cancelled the questionary.", False

            answers[key] = answer

        except KeyboardInterrupt:
            print_info("Questionary cancelled.")
            return "User cancelled the questionary.", False

    # Format answers back to the model as a readable summary
    lines = ["User answered the following questions:"]
    for k, v in answers.items():
        if isinstance(v, list):
            v_str = ", ".join(v) if v else "(none selected)"
        elif isinstance(v, bool):
            v_str = "yes" if v else "no"
        else:
            v_str = str(v) if v else "(empty)"
        lines.append(f"  {k}: {v_str}")

    print_info("Got it.")
    return "\n".join(lines), True
