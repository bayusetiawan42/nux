"""Backwards compatibility proxy for sharkyo.config."""

from sharkyo.config import (
    Config,
    RC_FILE,
    load_config,
    load_rc,
    rc_str,
    rc_int,
    rc_float,
)

__all__ = [
    "Config",
    "RC_FILE",
    "load_config",
    "load_rc",
    "rc_str",
    "rc_int",
    "rc_float",
]
