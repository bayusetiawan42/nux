# core/config.py
# Configuration management for Sharkyo (~/.sharkyorc).

import os
import re
from dataclasses import dataclass

RC_FILE: str = os.path.expanduser("~/.sharkyorc")

_SET_RE = re.compile(r"^set\s+(\S+)\s+(.+)$", re.IGNORECASE)


@dataclass
class Config:
    model: str = "openai/gpt-oss-120b"
    max_history: int = 12
    cmd_out_chars: int = 3000
    cmd_timeout: float = 0.0
    temperature: float = 0.7
    max_tokens: int = 512


def load_config() -> Config:
    cfg = Config()
    if not os.path.exists(RC_FILE):
        return cfg

    with open(RC_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            key: str | None = None
            val: str | None = None

            m = _SET_RE.match(line)
            if m:
                key, val = m.group(1).lower(), m.group(2).strip()
            elif "=" in line:
                k, _, v = line.partition("=")
                key, val = k.strip().lower(), v.strip()
            elif ":" in line:
                k, _, v = line.partition(":")
                key, val = k.strip().lower(), v.strip()

            if key and val and hasattr(cfg, key):
                target_type = type(getattr(cfg, key))
                try:
                    setattr(cfg, key, target_type(val))
                except (ValueError, TypeError):
                    pass

    return cfg
