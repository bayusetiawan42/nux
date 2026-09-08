# tools/questionary.py
# Interactive questionary tool.

from dataclasses import dataclass, field

import questionary as q

from sharkyo.core.config import Config
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import QUESTIONARY_STYLE_SPEC, console, is_interactive, print_info

SCHEMA = {
    "type": "function",
    "function": {
        "name": "QUESTIONARY",
        "strict": True,
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
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["questions"],
            "additionalProperties": False,
        },
    },
}

_STYLE = q.Style([*QUESTIONARY_STYLE_SPEC, ("answer", "fg:#00bcd4 bold")])

_CANCELLED = ToolResult(output="User cancelled the questionary.", should_continue=False)


@dataclass
class QuestionSpec:
    key: str
    type: str
    message: str
    choices: list[str] = field(default_factory=list)
    default: str | None = None

    @classmethod
    def from_dict(cls, spec: dict) -> "QuestionSpec":
        return cls(
            key=spec.get("key", "answer"),
            type=spec.get("type", "text"),
            message=spec.get("message", ""),
            choices=spec.get("choices", []),
            default=spec.get("default"),
        )


@dataclass
class QuestionaryArgs:
    intro: str
    questions: list[QuestionSpec]

    @classmethod
    def from_dict(cls, args: dict) -> "QuestionaryArgs":
        return cls(
            intro=args.get("intro", "").strip(),
            questions=[QuestionSpec.from_dict(s) for s in args.get("questions", [])],
        )


def _ask_one(spec: QuestionSpec) -> object | None:
    if spec.type == "text":
        kwargs: dict = {"style": _STYLE}
        if spec.default:
            kwargs["default"] = spec.default
        return q.text(spec.message, **kwargs).ask()

    if spec.type == "confirm":
        default_bool = str(spec.default).lower() in ("true", "yes", "1") if spec.default else False
        return q.confirm(spec.message, default=default_bool, style=_STYLE).ask()

    if spec.type == "select":
        if not spec.choices:
            return None
        kwargs = {"style": _STYLE}
        if spec.default and spec.default in spec.choices:
            kwargs["default"] = spec.default
        return q.select(spec.message, choices=spec.choices, **kwargs).ask()

    if spec.type == "checkbox":
        if not spec.choices:
            return []
        return q.checkbox(spec.message, choices=spec.choices, style=_STYLE).ask()

    return q.text(spec.message, style=_STYLE).ask()


def _format_answer(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(value) if value else "(none selected)"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value) if value else "(empty)"


def execute(args: dict, config: Config | None = None) -> ToolResult:
    parsed = QuestionaryArgs.from_dict(args)

    if not parsed.questions:
        return ToolResult(output="Error: 'questions' list is empty.", should_continue=True)

    if not is_interactive():
        return ToolResult(
            output=(
                "Error: cannot ask interactive questions because stdin is not a "
                "terminal. Proceed without asking."
            ),
            should_continue=True,
        )

    if parsed.intro:
        console.print(f"\n  [bold cyan]?[/bold cyan] {parsed.intro}\n")
    else:
        console.print()

    answers: dict[str, object] = {}

    for spec in parsed.questions:
        try:
            answer = _ask_one(spec)
        except KeyboardInterrupt:
            print_info("Questionary cancelled.")
            return _CANCELLED

        if answer is None and spec.type not in ("select", "checkbox"):
            print_info("Questionary cancelled.")
            return _CANCELLED

        answers[spec.key] = answer

    lines = ["User answered the following questions:"]
    for k, v in answers.items():
        lines.append(f"  {k}: {_format_answer(v)}")

    print_info("Got it.")
    return ToolResult(output="\n".join(lines), should_continue=True)
