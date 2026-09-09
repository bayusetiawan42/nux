# tools/__init__.py
# Tool registry and dispatcher for Nux.
# Each tool module uses @register_tool to register itself.

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

from nux.tools.result import ToolResult
from nux.ui.display import print_error

if TYPE_CHECKING:
    from nux.server.daemon import Session

_REGISTRY: dict[str, Callable[..., ToolResult]] = {}
TOOLS_SCHEMA: list[dict] = []


def register_tool(name: str):
    def decorator(function):
        module = sys.modules[function.__module__]

        schemas = getattr(module, "SCHEMAS", None)
        if schemas is not None:
            schema = schemas.get(name)
        else:
            schema = getattr(module, "SCHEMA", None)

        if schema is not None:
            TOOLS_SCHEMA.append(schema)
        if function is not None:
            _REGISTRY[name] = function

        return function

    return decorator


def dispatch_tool(name: str, args: dict, session: Session) -> ToolResult:
    handler = _REGISTRY.get(name)

    if not handler:
        print_error(f"Unknown tool requested: {name}")
        return ToolResult(output=f"Unknown tool: {name}", should_continue=False)

    return handler(args, session)


# Import tool modules to trigger @register_tool decorators
from nux.tools import (  # noqa: F401
    cmd,
    file,
    knowledge,
    questionary,
    skill,
)
