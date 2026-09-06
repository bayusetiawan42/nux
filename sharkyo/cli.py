"""CLI flag handlers for Sharkyo."""

import sys
import time

from sharkyo.apikeys import add_key, list_keys
from sharkyo.display import print_success, print_error, print_info, console
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager

_OPTIONS = [
    ('sharkyo "message"',              None,         "Chat with Sharkyo"),
    ("--add-key",                       "KEY",        "Add a Groq API key"),
    ("--add-key KEY --provider",        "openai",     "Add an OpenAI API key"),
    ("--add-key KEY --base-url",        "URL",        "Add a key with custom base URL"),
    ("--keys",                          None,         "List all API keys and their status"),
    ("--clear",                         None,         "Clear chat history"),
    ("--knowledge",                     None,         "Show stored knowledge"),
    ("--delete-knowledge",              "KEY",        "Delete a single knowledge entry"),
    ("--clear-knowledge",               None,         "Wipe all stored knowledge"),
    ("--help",                          None,         "Show this help message"),
]


def _print_help() -> None:
    console.print(f"\n[bold cyan]sharkyo[/bold cyan]  [dim]Your shark in the terminal[/dim]\n")
    console.print(f"[bold]Usage:[/bold] [cyan]sharkyo[/cyan] [dim]\"message\" [OPTIONS][/dim]\n")
    col_width = max(len(flag) + (len(arg) + 1 if arg else 0) for flag, arg, _ in _OPTIONS)
    for flag, arg, desc in _OPTIONS:
        plain    = flag + (f" {arg}" if arg else "")
        pad      = " " * (col_width - len(plain))
        flag_str = f"[bold dim]{flag}[/bold dim]"
        arg_str  = f" [dim]{arg}[/dim]" if arg else ""
        console.print(f"  {flag_str}{arg_str}{pad}  {desc}")
    console.print()


def _mask_key(key: str) -> str:
    """Show first 6 and last 4 chars, mask the rest."""
    if len(key) <= 12:
        return key[:3] + "..." + key[-2:]
    return key[:6] + "..." + key[-4:]


def handle_flags(args: list[str]) -> None:
    """Process CLI flags. Exits if a flag is handled."""

    if not args or "--help" in args or "-h" in args:
        _print_help()
        sys.exit(0)


    # --add-key KEY [--provider groq|openai] [--base-url URL]
    if "--add-key" in args:
        idx = args.index("--add-key")
        if idx + 1 >= len(args):
            print_error("--add-key requires a KEY argument.")
            sys.exit(1)
        key = args[idx + 1]
        provider = "groq"
        base_url = None
        if "--provider" in args:
            p_idx = args.index("--provider")
            if p_idx + 1 < len(args):
                provider = args[p_idx + 1]
        if "--base-url" in args:
            b_idx = args.index("--base-url")
            if b_idx + 1 < len(args):
                base_url = args[b_idx + 1]
        add_key(key, provider=provider, base_url=base_url)
        print_success(f"API key added (provider={provider}).")
        sys.exit(0)

    # --keys
    if "--keys" in args:
        keys = list_keys()
        if not keys:
            print_info("No API keys stored. Add one with: sharkyo --add-key KEY")
            sys.exit(0)
        now = int(time.time())
        console.print("[bold cyan]Stored API keys:[/bold cyan]")
        for k in keys:
            status = "[green]active[/green]" if k["active"] else "inactive"
            if k["reset_at"] > now:
                wait = k["reset_at"] - now
                status = f"[yellow]rate-limited ({wait}s)[/yellow]"
            masked = _mask_key(k["key"])
            base = f" base_url={k['base_url']}" if k["base_url"] else ""
            console.print(f"  [{k['id']}] {masked}  provider={k['provider']}{base}  {status}")
        sys.exit(0)

    # --clear
    if "--clear" in args:
        HistoryManager().clear()
        print_success("History cleared.")
        sys.exit(0)

    # --knowledge
    if "--knowledge" in args:
        entries = KnowledgeManager().list_all()
        if not entries:
            print_info("No knowledge stored yet.")
        else:
            console.print("[bold cyan]Stored knowledge:[/bold cyan]")
            for key, value in entries:
                console.print(f"  [cyan]{key}[/cyan] = {value}")
        sys.exit(0)

    # --clear-knowledge
    if "--clear-knowledge" in args:
        KnowledgeManager().clear()
        print_success("All knowledge cleared.")
        sys.exit(0)

    # --delete-knowledge KEY
    if "--delete-knowledge" in args:
        idx = args.index("--delete-knowledge")
        if idx + 1 >= len(args):
            print_error("--delete-knowledge requires a KEY argument.")
            sys.exit(1)
        key = args[idx + 1]
        deleted = KnowledgeManager().delete(key)
        if deleted:
            print_success(f"Deleted knowledge key: {key}")
        else:
            print_error(f"Key not found: {key}")
        sys.exit(0)
