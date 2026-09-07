# constants.py
# Static path constants for the Sharkyo application.
# Side effects (makedirs) are intentionally NOT here — call setup_dirs() from main().

import os

SHARKYO_DIR: str = os.path.expanduser("~/.sharkyo")
DB_FILE: str = os.path.join(SHARKYO_DIR, "data.db")
SKILLS_DIR: str = os.path.join(os.path.dirname(__file__), "skills")

# SYSTEM_PROMPT is imported from the generated module.
# To regenerate after editing skills/system_prompt.txt, run: python build_constants.py
from sharkyo._generated_constants import SYSTEM_PROMPT

__all__ = ["SHARKYO_DIR", "DB_FILE", "SKILLS_DIR", "SYSTEM_PROMPT"]


def setup_dirs() -> None:
    # Create required application directories.
    # Called explicitly from main() — never on import.
    os.makedirs(SHARKYO_DIR, exist_ok=True)
