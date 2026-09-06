"""Backwards compatibility proxy for sharkyo.tools."""

from sharkyo.config import load_config
from sharkyo.tools import dispatch_tool


def run_tool(name: str, args: dict) -> tuple[str | None, bool]:
    cfg = load_config()
    return dispatch_tool(name, args, cfg)


__all__ = ["run_tool"]
