# tools/__init__.py
# Tool registry and dispatcher for Sharkyo.

from sharkyo.config import Config
from sharkyo.display import print_error
from sharkyo.tools import cmd, knowledge, questionary, skill
from sharkyo.tools.result import ToolResult

TOOLS_SCHEMA = [
    cmd.SCHEMA,
    knowledge.SCHEMA,
    skill.SCHEMA,
    questionary.SCHEMA,
]

_REGISTRY: dict[str, callable] = {
    "CMD":         cmd.execute,
    "KNOWLEDGE":   knowledge.execute,
    "SKILL":       skill.execute,
    "QUESTIONARY": questionary.execute,
}


def dispatch_tool(name: str, args: dict, config: Config) -> ToolResult:
    # Dispatch a tool call by name to its handler.
    # Returns a ToolResult — never raises.
    handler = _REGISTRY.get(name)
    if not handler:
        print_error(f"Unknown tool requested: {name}")
        return ToolResult(output=f"Unknown tool: {name}", should_continue=False)
    return handler(args, config)
