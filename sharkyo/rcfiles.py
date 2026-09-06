"""RC file loader for Sharkyo configuration (~/.sharkyorc)."""

import os

RC_FILE = os.path.expanduser("~/.sharkyorc")

DEFAULTS: dict[str, str] = {
    "model": "openai/gpt-oss-120b",
    "max_history": "30",
    "cmd_out_chars": "10000",
    "cmd_out_lines": "30",
    "temperature": "0.7",
    "max_tokens": "1024",
}


def load_rc() -> dict[str, str]:
    """Load key=value pairs from RC_FILE, falling back to DEFAULTS."""
    config = dict(DEFAULTS)
    if not os.path.exists(RC_FILE):
        return config
    with open(RC_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


def rc_str(rc: dict[str, str], key: str) -> str:
    return rc.get(key, DEFAULTS.get(key, ""))


def rc_int(rc: dict[str, str], key: str) -> int:
    try:
        return int(rc.get(key, DEFAULTS.get(key, "0")))
    except ValueError:
        return int(DEFAULTS.get(key, "0"))


def rc_float(rc: dict[str, str], key: str) -> float:
    try:
        return float(rc.get(key, DEFAULTS.get(key, "0.0")))
    except ValueError:
        return float(DEFAULTS.get(key, "0.0"))
