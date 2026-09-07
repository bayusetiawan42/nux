# sharkyo/config.py
# Backward-compat re-export. Import from sharkyo.core.config instead.
from sharkyo.core.config import RC_FILE, Config, load_config

__all__ = ["RC_FILE", "Config", "load_config"]
