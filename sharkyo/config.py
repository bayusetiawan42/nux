"""Configuration management for Sharkyo (~/.sharkyorc)."""

from dataclasses import dataclass, field
import os
import re

RC_FILE = os.path.expanduser("~/.sharkyorc")


@dataclass
class Config:
    """Sharkyo configuration settings."""
    model: str = "openai/gpt-oss-120b"
    max_history: int = 30
    cmd_out_chars: int = 10000
    cmd_out_lines: int = 30
    temperature: float = 0.7
    max_tokens: int = 1024


_SET_RE = re.compile(r"^set\s+(\S+)\s+(.+)$", re.IGNORECASE)


def load_config() -> Config:
    """Load configuration from ~/.sharkyorc, with sensible defaults."""
    cfg = Config()
    if not os.path.exists(RC_FILE):
        return cfg

    with open(RC_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            key, val = None, None

            # Support 'set key value'
            m = _SET_RE.match(line)
            if m:
                key, val = m.group(1).lower(), m.group(2).strip()
            # Support 'key = value' or 'key: value'
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


# Backwards compatibility helpers
def load_rc() -> dict[str, str]:
    cfg = load_config()
    return {
        "model": cfg.model,
        "max_history": str(cfg.max_history),
        "cmd_out_chars": str(cfg.cmd_out_chars),
        "cmd_out_lines": str(cfg.cmd_out_lines),
        "temperature": str(cfg.temperature),
        "max_tokens": str(cfg.max_tokens),
    }


def rc_str(rc: dict, key: str) -> str:
    return rc.get(key, "")


def rc_int(rc: dict, key: str) -> int:
    return int(rc.get(key, 0))


def rc_float(rc: dict, key: str) -> float:
    return float(rc.get(key, 0.0))
