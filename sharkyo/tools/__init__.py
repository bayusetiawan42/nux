"""Tool registry and dispatcher for Sharkyo."""

from sharkyo.config import Config
from sharkyo.display import print_error
from sharkyo.tools import cmd, knowledge, skill, websearch

TOOLS_SCHEMA = [
    cmd.SCHEMA,
    knowledge.SCHEMA,
    skill.SCHEMA,
    websearch.SCHEMA,
]

_REGISTRY = {
    "CMD": cmd.execute,
    "KNOWLEDGE": knowledge.execute,
    "SKILL": skill.execute,
    "WEBSEARCH": websearch.execute,
}


def dispatch_tool(name: str, args: dict, config: Config) -> tuple[str | None, bool]:
    """Dispatch a tool execution by name.

    Returns:
        (tool_output_for_model, should_continue_loop)
    """
    handler = _REGISTRY.get(name)
    if not handler:
        print_error(f"Unknown tool requested: {name}")
        return f"Unknown tool: {name}", False
    return handler(args, config)
