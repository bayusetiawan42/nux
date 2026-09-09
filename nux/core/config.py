# core/config.py
# Configuration management for Nux (~/.nuxrc).

import os
import re
from dataclasses import dataclass, fields

RC_FILE: str = os.path.expanduser("~/.nuxrc")
_SET_RE = re.compile(r"^set\s+(\S+)\s+(.+)$", re.IGNORECASE)

_DEFAULTS = None  # populated after Config is defined


@dataclass
class Config:
    model: str = "openai/gpt-oss-20b"
    max_history: int = 12
    max_command_output_display: int = 2000  # chars
    max_command_output_tokens: int = 1200  # tokens
    max_completion_tokens: int = 512
    temperature: float = 0.7
    reasoning_effort: str | None = None
    service_tier: str | None = None
    user: str | None = None


_DEFAULTS = {f.name: f.default for f in fields(Config)}


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


def get_config(config: Config | None = None) -> Config:
    return config if config is not None else load_config()


def _fetch_context_window(model: str, key: str, base_url: str | None = None) -> int | None:
    # Query Groq API for a model's context_window. Returns None on failure.
    try:
        import importlib

        groq = importlib.import_module("groq")
        client = groq.Groq(api_key=key, base_url=base_url)
        resp = client.models.retrieve(model)
        return getattr(resp, "context_window", None)
    except Exception:  # noqa: BLE001
        return None


def auto_adjust_config(cfg: Config, key: str, base_url: str | None = None) -> Config:
    # Adjust max_history and max_command_output_tokens from context_window
    # when the user hasn't explicitly overridden the defaults.
    ctx = _fetch_context_window(cfg.model, key, base_url)
    if ctx is None:
        return cfg

    # Only auto-adjust fields still at their defaults
    # Reserve ~40% for system prompt + completion headroom (hemat usage).
    usable = int(ctx * 0.6)

    if cfg.max_history == _DEFAULTS["max_history"]:
        # each history message ~300 tokens; keep history compact
        cfg.max_history = max(3, min(usable // 400, 25))

    if cfg.max_command_output_tokens == _DEFAULTS["max_command_output_tokens"]:
        # Command output takes up to ~1/10 of usable context
        cfg.max_command_output_tokens = max(400, min(usable // 10, 4000))

    return cfg
