# cli.py
# CLI flag handlers and help display for Sharkyo.

import sys
import time

from sharkyo.apikeys import add_key, list_keys
from sharkyo.display import console, print_error, print_info, print_success
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager

_OPTIONS: list[tuple[str, str | None, str]] = [
    ('sharkyo "message"',                None,        "Chat with Sharkyo"),
    ("--add-key",                         "KEY",       "Add an API key (Groq by default)"),
    ("--add-key KEY --provider",          "PROVIDER",  "Set provider (groq | openai)"),
    ("--add-key KEY --base-url",          "URL",       "Set custom base URL"),
    ("--keys",                            None,        "List all stored API keys and rate-limit status"),
    ("--clear",                           None,        "Clear chat history"),
    ("--knowledge",                       None,        "Show stored persistent facts"),
    ("--delete-knowledge",                "KEY",       "Delete a single knowledge entry"),
    ("--clear-knowledge",                 None,        "Wipe all stored knowledge"),
    ("--help",                            None,        "Show this help menu"),
]


def print_help() -> None:
    # Render the user-friendly CLI help menu.
    console.print("\n[bold cyan]sharkyo[/bold cyan]  [dim]Shark, yo. Operate the system![/dim]\n")
    console.print("[bold]Usage:[/bold] [cyan]sharkyo[/cyan] [dim]\"message\" [OPTIONS][/dim]\n")
    col_width = max(len(flag) + (len(arg) + 1 if arg else 0) for flag, arg, _ in _OPTIONS)
    for flag, arg, desc in _OPTIONS:
        plain = flag + (f" {arg}" if arg else "")
        pad = " " * (col_width - len(plain))
        flag_str = f"[bold dim]{flag}[/bold dim]"
        arg_str = f" [dim]{arg}[/dim]" if arg else ""
        console.print(f"  {flag_str}{arg_str}{pad}  {desc}")
    console.print()


def _mask_key(key: str) -> str:
    # Mask an API key for safe display, preserving only a few chars at each end.
    if len(key) <= 12:
        return key[:3] + "..." + key[-2:]
    return key[:6] + "..." + key[-4:]


def _get_arg_after(args: list[str], flag: str) -> str | None:
    # Return the value immediately following a flag, or None if absent/missing.
    if flag not in args:
        return None
    idx = args.index(flag)
    if idx + 1 >= len(args):
        return None
    return args[idx + 1]


def handle_flags(args: list[str]) -> bool:
    # Handle CLI flags. Returns True if a flag was handled and process should exit.
    if not args or "--help" in args or "-h" in args:
        print_help()
        sys.exit(0)

    if "--add-key" in args:
        key = _get_arg_after(args, "--add-key")
        if not key:
            print_error("--add-key requires a KEY argument.")
            sys.exit(1)
        provider = _get_arg_after(args, "--provider") or "groq"
        base_url = _get_arg_after(args, "--base-url")
        add_key(key, provider=provider, base_url=base_url)
        print_success(f"API key added (provider={provider}).")
        sys.exit(0)

    if "--keys" in args:
        keys = list_keys()
        if not keys:
            print_info("No API keys stored. Add one with: sharkyo --add-key KEY")
            sys.exit(0)
        now = int(time.time())
        console.print("[bold cyan]Stored API keys:[/bold cyan]")
        for k in keys:
            if k.reset_at > now:
                wait = k.reset_at - now
                status = f"[yellow]rate-limited ({wait}s remaining)[/yellow]"
            elif k.active:
                status = "[green]active[/green]"
            else:
                status = "inactive"
            masked = _mask_key(k.key)
            base = f" base_url={k.base_url}" if k.base_url else ""
            console.print(f"  [{k.id}] {masked}  provider={k.provider}{base}  {status}")
        sys.exit(0)

    if "--clear" in args:
        HistoryManager().clear()
        print_success("History cleared.")
        sys.exit(0)

    if "--knowledge" in args:
        entries = KnowledgeManager().list_all()
        if not entries:
            print_info("No knowledge stored yet.")
        else:
            console.print("[bold cyan]Stored knowledge:[/bold cyan]")
            for key, value in entries:
                console.print(f"  [cyan]{key}[/cyan] = {value}")
        sys.exit(0)

    if "--clear-knowledge" in args:
        KnowledgeManager().clear()
        print_success("All knowledge cleared.")
        sys.exit(0)

    if "--delete-knowledge" in args:
        key = _get_arg_after(args, "--delete-knowledge")
        if not key:
            print_error("--delete-knowledge requires a KEY argument.")
            sys.exit(1)
        deleted = KnowledgeManager().delete(key)
        if deleted:
            print_success(f"Deleted knowledge key: {key}")
        else:
            print_error(f"Key not found: {key}")
        sys.exit(0)

    return False
