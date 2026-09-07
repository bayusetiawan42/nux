# sharkyo/constants.py
# Backward-compat re-export. Import from sharkyo.core.constants instead.
from sharkyo.core.constants import DB_FILE, SHARKYO_DIR, SKILLS_DIR, SYSTEM_PROMPT, setup_dirs

__all__ = ["DB_FILE", "SHARKYO_DIR", "SKILLS_DIR", "SYSTEM_PROMPT", "setup_dirs"]
