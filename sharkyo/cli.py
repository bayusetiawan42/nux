# cli.py
# CLI argument parsing and handlers for Sharkyo.

import argparse
import sys
import time

from sharkyo.apikeys import add_key, list_keys
from sharkyo.display import console, print_error, print_info, print_success
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager


def build_parser() -> argparse.ArgumentParser:
    # Build the Sharkyo CLI parser.
    parser = argparse.ArgumentParser(
        prog="sharkyo",
        description="Shark, yo. Operate the system!",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        metavar="message",
        help='the task to run, e.g. "compress this folder"',
    )
    parser.add_argument("--add-key", metavar="KEY", help="add an API key (Groq by default)")
    parser.add_argument("--provider", metavar="PROVIDER", help="set provider for --add-key (groq | openai)")
    parser.add_argument("--base-url", metavar="URL", help="set custom base URL for --add-key")
    parser.add_argument("--keys", action="store_true", help="list stored API keys and rate-limit status")
    parser.add_argument("--clear", action="store_true", help="clear chat history")
    parser.add_argument("--knowledge", action="store_true", help="show stored persistent facts")
    parser.add_argument("--delete-knowledge", metavar="KEY", help="delete a single knowledge entry")
    parser.add_argument("--clear-knowledge", action="store_true", help="wipe all stored knowledge")
    return parser


def _mask_key(key: str) -> str:
    # Mask an API key for safe display, preserving only a few chars at each end.
    if len(key) <= 12:
        return key[:3] + "..." + key[-2:]
    return key[:6] + "..." + key[-4:]


def _print_keys() -> None:
    keys = list_keys()
    if not keys:
        print_info("No API keys stored. Add one with: sharkyo --add-key KEY")
        return
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


def _print_knowledge() -> None:
    entries = KnowledgeManager().list_all()
    if not entries:
        print_info("No knowledge stored yet.")
        return
    console.print("[bold cyan]Stored knowledge:[/bold cyan]")
    for key, value in entries:
        console.print(f"  [cyan]{key}[/cyan] = {value}")


def _handle_server(argv: list[str] | None) -> int | None:
    # Handle the `sharkyo server <start|stop|status>` subcommand.
    # Returns an exit code to use, or None to continue into agent dispatch.
    sub = argv[0] if argv else "start"
    from sharkyo import client
    from sharkyo.server import running, stop

    if sub == "status":
        if running():
            print_success("sharkyo server is running.")
        else:
            print_info("sharkyo server is not running.")
        return 0

    if sub == "stop":
        if stop():
            print_success("sharkyo server stopped.")
        else:
            print_info("No sharkyo server running.")
        return 0

    if sub == "start":
        if running():
            print_info("sharkyo server is already running.")
            return 0
        client.start_daemon()
        # Wait briefly for the daemon to bind its socket before reporting.
        for _ in range(40):
            if running():
                print_success("sharkyo server started.")
                return 0
            time.sleep(0.1)
        print_info("sharkyo server starting in the background...")
        return 0

    print_error(f"Unknown server command: {sub}")
    print_info("Usage: sharkyo server <start|stop|status>")
    return 1


def main() -> str:
    # Parse CLI args and handle flags. Returns the user prompt (non-empty).
    args = build_parser().parse_args()

    if args.add_key:
        provider = args.provider or "groq"
        add_key(args.add_key, provider=provider, base_url=args.base_url)
        print_success(f"API key added (provider={provider}).")
        sys.exit(0)

    if args.keys:
        _print_keys()
        sys.exit(0)

    if args.clear:
        HistoryManager().clear()
        print_success("History cleared.")
        sys.exit(0)

    if args.knowledge:
        _print_knowledge()
        sys.exit(0)

    if args.clear_knowledge:
        KnowledgeManager().clear()
        print_success("All knowledge cleared.")
        sys.exit(0)

    if args.delete_knowledge:
        deleted = KnowledgeManager().delete(args.delete_knowledge)
        if deleted:
            print_success(f"Deleted knowledge key: {args.delete_knowledge}")
        else:
            print_error(f"Key not found: {args.delete_knowledge}")
        sys.exit(0)

    prompt = " ".join(args.prompt).strip()

    # `sharkyo server <start|stop|status>` — the first free argument names it.
    if prompt == "server":
        sys.exit(_handle_server([]))
    if prompt.startswith("server "):
        sys.exit(_handle_server(prompt[len("server "):].split()))

    if not prompt:
        build_parser().print_help()
        sys.exit(0)
    return prompt
