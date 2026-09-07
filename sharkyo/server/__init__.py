# server/__init__.py
# Server package: daemon lifecycle and client for warm-start execution.

from sharkyo.server.client import run_remote, start_daemon
from sharkyo.server.daemon import (
    register_turn_runner,
    run_forever,
    running,
    stop,
)

__all__ = [
    "register_turn_runner",
    "run_forever",
    "run_remote",
    "running",
    "start_daemon",
    "stop",
]
