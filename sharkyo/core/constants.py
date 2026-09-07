# core/constants.py
# Static paths and text constants for the Sharkyo application.

import os
from importlib.resources import files

SHARKYO_DIR: str = os.path.expanduser("~/.sharkyo")
DB_FILE: str = os.path.join(SHARKYO_DIR, "data.db")

_PKG_DIR = files("sharkyo")
SKILLS_DIR: str = str(_PKG_DIR / "skills")
SYSTEM_PROMPT: str = (
    (_PKG_DIR / "skills" / "system_prompt.txt").read_text(encoding="utf-8").rstrip()
)

__all__ = ["DB_FILE", "SHARKYO_DIR", "SKILLS_DIR", "SYSTEM_PROMPT"]


def setup_dirs() -> None:
    os.makedirs(SHARKYO_DIR, exist_ok=True)
