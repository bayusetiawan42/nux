# cli.py
# CLI argument parsing and handlers for Sharkyo.

import argparse
import sys
import time

from sharkyo.storage.apikeys import add_key, list_keys
from sharkyo.storage.history import HistoryManager
from sharkyo.storage.knowledge import KnowledgeManager
from sharkyo.ui.display import console, print_error, print_info, print_success


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sharkyo",
        description="Shark, yo. Operate the system!",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
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
    sub = argv[0] if argv else "start"
    from sharkyo.server import running, start_daemon, stop

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
        start_daemon()
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


def _handle_command(argv: list[str] | None) -> int | None:
    if not argv:
        print_info("Available commands: keys, clear, knowledge, clear-knowledge, server")
        print_info("Usage: sharkyo command <name> [args]")
        return 0

    name = argv[0]
    cmd_args = argv[1:]

    if name == "keys":
        _print_keys()
        return 0

    if name == "clear":
        HistoryManager().clear()
        print_success("History cleared.")
        return 0

    if name == "knowledge":
        _print_knowledge()
        return 0

    if name == "clear-knowledge":
        KnowledgeManager().clear()
        print_success("All knowledge cleared.")
        return 0

    if name == "delete-knowledge":
        if not cmd_args:
            print_error("Usage: sharkyo command delete-knowledge <key>")
            return 1
        deleted = KnowledgeManager().delete(cmd_args[0])
        if deleted:
            print_success(f"Deleted knowledge key: {cmd_args[0]}")
        else:
            print_error(f"Key not found: {cmd_args[0]}")
        return 0

    if name == "server":
        return _handle_server(cmd_args)

    print_error(f"Unknown command: {name}")
    print_info("Available commands: keys, clear, knowledge, clear-knowledge, delete-knowledge, server")
    return 1


def main() -> str:
    args = build_parser().parse_args()

    # Run all flag-based actions (can combine multiple flags)
    ran_action = False

    if args.add_key:
        provider = args.provider or "groq"
        add_key(args.add_key, provider=provider, base_url=args.base_url)
        print_success(f"API key added (provider={provider}).")
        ran_action = True

    if args.keys:
        _print_keys()
        ran_action = True

    if args.clear:
        HistoryManager().clear()
        print_success("History cleared.")
        ran_action = True

    if args.knowledge:
        _print_knowledge()
        ran_action = True

    if args.clear_knowledge:
        KnowledgeManager().clear()
        print_success("All knowledge cleared.")
        ran_action = True

    if args.delete_knowledge:
        deleted = KnowledgeManager().delete(args.delete_knowledge)
        if deleted:
            print_success(f"Deleted knowledge key: {args.delete_knowledge}")
        else:
            print_error(f"Key not found: {args.delete_knowledge}")
        ran_action = True

    prompt = " ".join(args.prompt).strip()

    # Handle subcommands: server, command
    if prompt.startswith("server ") or prompt == "server":
        parts = prompt.split(None, 1)
        sys.exit(_handle_server(parts[1].split() if len(parts) > 1 else []))

    if prompt.startswith("command ") or prompt == "command":
        parts = prompt.split(None, 1)
        sys.exit(_handle_command(parts[1].split() if len(parts) > 1 else []))

    # If we ran actions but there's no prompt, exit
    if ran_action and not prompt:
        sys.exit(0)

    # If there's a prompt, return it for the agent
    if prompt:
        return prompt

    # Nothing to do, show help
    build_parser().print_help()
    sys.exit(0)
