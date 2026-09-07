# constants.py
# Static paths and text constants for the Sharkyo application.
# Side effects (makedirs) are intentionally NOT here — call setup_dirs() from main().

import os
from importlib.resources import files

SHARKYO_DIR: str = os.path.expanduser("~/.sharkyo")
DB_FILE: str = os.path.join(SHARKYO_DIR, "data.db")

_PKG_DIR = files("sharkyo")
SKILLS_DIR: str = str(_PKG_DIR / "skills")
SYSTEM_PROMPT: str = (
    (_PKG_DIR / "skills" / "system_prompt.txt").read_text(encoding="utf-8").rstrip()
)

__all__ = ["SHARKYO_DIR", "DB_FILE", "SKILLS_DIR", "SYSTEM_PROMPT"]


def setup_dirs() -> None:
    # Create required application directories.
    # Called explicitly from main() — never on import.
    os.makedirs(SHARKYO_DIR, exist_ok=True)
