# tools/skill.py
# Internal skill discovery tool.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sharkyo.core.config import Config
from sharkyo.search import search_skills
from sharkyo.tools import register_tool
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import print_info

if TYPE_CHECKING:
    from sharkyo.server.protocol import Packet

SCHEMA = {
    "type": "function",
    "function": {
        "name": "SKILL",
        "strict": True,
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
            "additionalProperties": False,
        },
    },
}


@dataclass
class SkillArgs:
    query: str

    @classmethod
    def from_dict(cls, args: dict) -> SkillArgs:
        return cls(query=args.get("query", "").strip())


@register_tool("SKILL")
def execute(args: dict, config: Config | None, packet: Packet) -> ToolResult:
    parsed = SkillArgs.from_dict(args)
    if not parsed.query:
        return ToolResult(
            output="Error: 'query' parameter is required for SKILL search.",
            should_continue=True,
        )

    skill = search_skills(parsed.query)

    if skill:
        print_info(f"Retrieved skill: {skill.name}")
        content = f"Skill '{skill.name}':\n{skill.content.strip()}"
        return ToolResult(output=content, should_continue=True)

    return ToolResult(
        output=f"No internal skill found matching '{parsed.query}'. Proceed using standard tools.",
        should_continue=True,
    )
