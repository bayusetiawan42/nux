# tools/__init__.py
# Tool registry and dispatcher for Sharkyo.
# Each tool module uses @register_tool to register itself.

from collections.abc import Callable

from sharkyo.core.config import Config
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import print_error

_REGISTRY: dict[str, Callable[..., ToolResult]] = {}
TOOLS_SCHEMA: list[dict] = []


def register_tool(name: str):
    def decorator(module):
        schema = getattr(module, "SCHEMA", None)
        execute_fn = getattr(module, "execute", None)
        if schema is not None:
            TOOLS_SCHEMA.append(schema)
        if execute_fn is not None:
            _REGISTRY[name] = execute_fn
        return module

    return decorator


def dispatch_tool(name: str, args: dict, config: Config) -> ToolResult:
    handler = _REGISTRY.get(name)
    if not handler:
        print_error(f"Unknown tool requested: {name}")
        return ToolResult(output=f"Unknown tool: {name}", should_continue=False)
    return handler(args, config)


# Import tool modules to trigger @register_tool decorators
from sharkyo.tools import cmd, knowledge, questionary, skill  # noqa: F401
