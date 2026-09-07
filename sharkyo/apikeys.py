# sharkyo/apikeys.py
# Backward-compat re-export. Import from sharkyo.storage.apikeys instead.
from sharkyo.storage.apikeys import (
    ApiKey,
    active_key,
    add_key,
    has_keys,
    list_keys,
    rotate_active,
    save_rate_limit,
    set_active,
)

__all__ = [
    "ApiKey",
    "active_key",
    "add_key",
    "has_keys",
    "list_keys",
    "rotate_active",
    "save_rate_limit",
    "set_active",
]
