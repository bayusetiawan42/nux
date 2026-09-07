# sharkyo/db.py
# Backward-compat re-export. Import from sharkyo.storage.db instead.
from sharkyo.storage.db import get_connection

__all__ = ["get_connection"]
