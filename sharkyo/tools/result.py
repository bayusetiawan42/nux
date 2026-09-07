# tools/result.py
# Shared return type for all tool execute() functions.

from dataclasses import dataclass


@dataclass
class ToolResult:
    # Result returned by every tool execute() function.
    # output: text to send back to the model (None = nothing to send).
    # should_continue: whether the agentic loop should keep running.
    output: str | None
    should_continue: bool
