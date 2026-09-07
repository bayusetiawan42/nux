# tools/__init__.py
# Tool registry and dispatcher for Sharkyo.

from collections.abc import Callable

from sharkyo.core.config import Config
from sharkyo.tools import cmd, knowledge, questionary, skill
from sharkyo.tools.result import ToolResult
from sharkyo.tools.schema import TOOLS_SCHEMA as TOOLS_SCHEMA
from sharkyo.ui.display import print_error

_REGISTRY: dict[str, Callable[..., ToolResult]] = {
    "CMD":         cmd.execute,
    "KNOWLEDGE":   knowledge.execute,
    "SKILL":       skill.execute,
    "QUESTIONARY": questionary.execute,
}


def dispatch_tool(name: str, args: dict, config: Config) -> ToolResult:
    handler = _REGISTRY.get(name)
    if not handler:
        print_error(f"Unknown tool requested: {name}")
        return ToolResult(output=f"Unknown tool: {name}", should_continue=False)
    return handler(args, config)
