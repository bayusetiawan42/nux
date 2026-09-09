# ui/__init__.py
# Display utilities for Nux.

from nux.ui.display import (
    QUESTIONARY_STYLE_SPEC,
    console,
    is_interactive,
    print_error,
    print_info,
    print_reply,
    print_success,
    show_diff,
    show_file_preview,
    unified_diff,
    yaspin_if_tty,
)

__all__ = [
    "QUESTIONARY_STYLE_SPEC",
    "console",
    "is_interactive",
    "print_error",
    "print_info",
    "print_reply",
    "print_success",
    "show_diff",
    "show_file_preview",
    "unified_diff",
    "yaspin_if_tty",
]
