# tools/skill.py
# Internal skill discovery tool.

from dataclasses import dataclass

from sharkyo.core.config import Config
from sharkyo.search import search_skills
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import print_info

SCHEMA = {
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
}


@dataclass
class SkillArgs:
    query: str

    @classmethod
    def from_dict(cls, args: dict) -> "SkillArgs":
        return cls(query=args.get("query", "").strip())


def execute(args: dict, config: Config | None = None) -> ToolResult:
    parsed = SkillArgs.from_dict(args)
    if not parsed.query:
        return ToolResult(
            output="Error: 'query' parameter is required for SKILL search.",
            should_continue=True,
        )

    guide = search_skills(parsed.query)
    if guide:
        print_info(f"Retrieved internal skill for: [bold cyan]{parsed.query}[/bold cyan]")
        return ToolResult(output=guide, should_continue=True)

    return ToolResult(
        output=f"No internal skill found matching '{parsed.query}'. Proceed using standard tools.",
        should_continue=True,
    )
