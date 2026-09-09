# core/error_logger.py
# Centralized error logging to ~/.sharkyo/error/

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, timezone

ERROR_DIR = os.path.join(os.path.expanduser("~/.sharkyo"), "error")
ERROR_LOG = os.path.join(ERROR_DIR, "error.log")
HISTORY_JSON = os.path.join(ERROR_DIR, "history.json")


def _ensure_dir() -> None:
    os.makedirs(ERROR_DIR, exist_ok=True)


def log_error(
    error: Exception,
    context: str = "",
    messages: list[dict] | None = None,
) -> None:
    _ensure_dir()

    ts = datetime.now(timezone.utc).isoformat()
    tb = traceback.format_exc()

    entry = {
        "timestamp": ts,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "traceback": tb,
    }

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{ts}] {context}\n" if context else f"[{ts}]\n")
        f.write(f"Error: {type(error).__name__}: {error}\n")
        f.write(f"Traceback:\n{tb}\n")

    if messages is not None:
        _save_history(messages)


def log_raw(title: str, detail: str) -> None:
    _ensure_dir()

    ts = datetime.now(timezone.utc).isoformat()

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{ts}] {title}\n")
        f.write(f"{detail}\n")


def _save_history(messages: list[dict]) -> None:
    _ensure_dir()

    serializable = []
    for msg in messages:
        entry = {"role": msg.get("role"), "content": msg.get("content")}
        if "tool_calls" in msg:
            entry["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg:
            entry["tool_call_id"] = msg["tool_call_id"]
        serializable.append(entry)

    with open(HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
