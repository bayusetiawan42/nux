# tools/result.py
# Shared return type and serialization for tool operations.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from groq.types.chat import ChatCompletionMessageToolCall


@dataclass
class ToolResult:
    # Result returned by every tool execute() function.
    # output: text to send back to the model (None = nothing to send).
    # should_continue: whether the agentic loop should keep running.
    output: str | None
    should_continue: bool


def serialize_tool_call(tc: ChatCompletionMessageToolCall | dict) -> dict:
    if isinstance(tc, dict):
        return {
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"],
            },
        }
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        },
    }
