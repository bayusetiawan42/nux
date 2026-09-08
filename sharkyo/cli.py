# cli.py
# CLI argument parsing and handlers for Sharkyo.

import sys
import time
from dataclasses import dataclass

from sharkyo.storage.apikeys import active_key, add_key, list_keys
from sharkyo.storage.history import HistoryManager
from sharkyo.tools.knowledge import clear_all, delete_key, list_all_formatted
from sharkyo.ui.display import console, print_error, print_info, print_success

AVAILABLE_COMMANDS = "keys, clear, knowledge, clear-knowledge, delete-knowledge, server, reload"

_MSG_HISTORY_CLEARED = "History cleared."
_MSG_NO_KNOWLEDGE = "No knowledge stored yet."


@dataclass
class CliArgs:
    prompt: list[str]
    add_key: str | None = None
    base_url: str | None = None
    keys: bool = False
    models: str | None = None  # None = flag only, str = key index
    clear: bool = False
    knowledge: bool = False
    delete_knowledge: str | None = None
    clear_knowledge: bool = False


_DESCRIPTION = "Shark, yo. Operate the system!"

_COMMANDS = [
    ("sharkyo <message>", "run a task"),
    ("sharkyo server <start|stop|status|reload>", "manage the background daemon"),
    ("sharkyo reload", "restart the background daemon"),
    ("sharkyo command <name> [args]", "run a built-in command"),
]

_OPTIONS = [
    ("--add-key <key>", "add a Groq API key"),
    ("--base-url <url>", "set custom base URL for --add-key"),
    ("--keys", "list stored API keys and rate-limit status"),
    ("--models [KEY_INDEX]", "list available models for current or specific key"),
    ("--clear", "clear chat history"),
    ("--knowledge", "show stored persistent facts"),
    ("--delete-knowledge <key>", "delete a single knowledge entry"),
    ("--clear-knowledge", "wipe all stored knowledge"),
    ("-h, --help", "show this help message and exit"),
]

_EXAMPLES = [
    'sharkyo "compress this folder"',
    "sharkyo --clear --clear-knowledge",
    'sharkyo --clear -- "Change this repo to private"',
    "sharkyo command keys",
    "sharkyo server status",
    "sharkyo reload",
]


def _col_width(items: list[tuple[str, str]]) -> int:
    return max(len(syn) for syn, _ in items) + 2


def print_help() -> None:
    w = _col_width(_COMMANDS)
    print("Usage: sharkyo [options] [message...]\n")
    print("Commands:")
    for syn, desc in _COMMANDS:
        print(f"  {syn:<{w}}{desc}")
    print()
    print("Options:")
    w = _col_width(_OPTIONS)
    for syn, desc in _OPTIONS:
        print(f"  {syn:<{w}}{desc}")
    print()
    print("Examples:")
    for ex in _EXAMPLES:
        print(f"  {ex}")


def parse(argv: list[str] | None = None) -> CliArgs:
    if argv is None:
        argv = sys.argv[1:]

    args = CliArgs(prompt=[])

    i = 0
    n = len(argv)
    while i < n:
        arg = argv[i]

        # -- means everything after is the prompt
        if arg == "--":
            args.prompt = argv[i + 1 :]
            break

        if arg == "-h" or arg == "--help":
            print_help()
            sys.exit(0)

        if arg == "--add-key":
            i += 1
            if i >= n:
                print_error("--add-key requires a value")
                sys.exit(1)
            args.add_key = argv[i]
        elif arg == "--base-url":
            i += 1
            if i >= n:
                print_error("--base-url requires a value")
                sys.exit(1)
            args.base_url = argv[i]
        elif arg == "--delete-knowledge":
            i += 1
            if i >= n:
                print_error("--delete-knowledge requires a value")
                sys.exit(1)
            args.delete_knowledge = argv[i]
        elif arg == "--keys":
            args.keys = True
        elif arg == "--models" or arg.startswith("--models="):
            # --models alone, or --models=INDEX
            if "=" in arg:
                args.models = arg.split("=", 1)[1] or ""
            elif i + 1 < n and not argv[i + 1].startswith("-"):
                i += 1
                args.models = argv[i]
            else:
                args.models = ""
        elif arg == "--clear":
            args.clear = True
        elif arg == "--knowledge":
            args.knowledge = True
        elif arg == "--clear-knowledge":
            args.clear_knowledge = True
        elif arg.startswith("-"):
            print_error(f"Unknown option: {arg}")
            print_info("Use --help to see available options")
            sys.exit(1)
        else:
            # Positional: append to prompt
            args.prompt.append(arg)

        i += 1

    return args


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
        console.print(f"  [{k.id}] {masked}{base}  {status}")


def _print_knowledge() -> None:
    formatted = list_all_formatted()
    if not formatted:
        print_info(_MSG_NO_KNOWLEDGE)
        return
    console.print("[bold cyan]Stored knowledge:[/bold cyan]")
    for line in formatted.splitlines():
        key, _, value = line.partition("=")
        console.print(f"  [cyan]{key.strip()}[/cyan] = {value.strip()}")


def _print_models(key_index: str | None) -> None:
    keys = list_keys()
    if not keys:
        print_info("No API keys stored. Add one with: sharkyo --add-key KEY")
        return

    from sharkyo.core.llm import Groq

    if key_index:
        idx = int(key_index)
        match = [k for k in keys if k.id == idx]
        if not match:
            print_error(f"Key index {idx} not found. Use --keys to see available indices.")
            return
        target_key = match[0]
    else:
        target_key = active_key() or keys[0]

    try:
        client = Groq()(api_key=target_key.key, base_url=target_key.base_url)
        response = client.models.list()
    except Exception as e:  # noqa: BLE001
        print_error(f"Failed to fetch models: {e}")
        return

    models = response.data
    if not models:
        print_info("No models available for this API key.")
        return

    label = f"key [{target_key.id}]" if key_index else "active key"
    console.print(f"[bold cyan]Available models ({label}):[/bold cyan]")
    for m in models:
        ctx = getattr(m, "context_window", None)
        ctx_str = f" ctx={ctx:,}" if ctx else ""
        owner = getattr(m, "owned_by", "")
        owner_str = f"  ({owner})" if owner else ""
        console.print(f"  [green]{m.id}[/green]{ctx_str}{owner_str}")


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

    if sub == "reload":
        stop()
        start_daemon()
        for _ in range(40):
            if running():
                print_success("sharkyo server reloaded.")
                return 0
            time.sleep(0.1)
        print_info("sharkyo server reloading in the background...")
        return 0

    print_error(f"Unknown server command: {sub}")
    print_info("Usage: sharkyo server <start|stop|status|reload>")
    return 1


def _handle_command(argv: list[str] | None) -> int | None:
    if not argv:
        print_info(f"Available commands: {AVAILABLE_COMMANDS}")
        print_info("Usage: sharkyo command <name> [args]")
        return 0

    name = argv[0]
    cmd_args = argv[1:]

    if name == "keys":
        _print_keys()
        return 0

    if name == "clear":
        HistoryManager().clear()
        print_success(_MSG_HISTORY_CLEARED)
        return 0

    if name == "knowledge":
        _print_knowledge()
        return 0

    if name == "clear-knowledge":
        clear_all()
        return 0

    if name == "delete-knowledge":
        if not cmd_args:
            print_error("Usage: sharkyo command delete-knowledge <key>")
            return 1
        success, msg = delete_key(cmd_args[0])
        if success:
            print_success(msg)
        else:
            print_error(msg)
        return 0

    if name == "server":
        return _handle_server(cmd_args)

    print_error(f"Unknown command: {name}")
    print_info(f"Available commands: {AVAILABLE_COMMANDS}")
    return 1


def main() -> str:
    args = parse()

    # Run all flag-based actions (can combine multiple flags)
    ran_action = False

    if args.add_key:
        add_key(args.add_key, base_url=args.base_url)
        print_success("API key added.")
        ran_action = True

    if args.keys:
        _print_keys()
        ran_action = True

    if args.models is not None:
        _print_models(args.models or None)
        ran_action = True

    if args.clear:
        HistoryManager().clear()
        print_success(_MSG_HISTORY_CLEARED)
        ran_action = True

    if args.knowledge:
        _print_knowledge()
        ran_action = True

    if args.clear_knowledge:
        clear_all()
        ran_action = True

    if args.delete_knowledge:
        success, msg = delete_key(args.delete_knowledge)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        ran_action = True

    prompt = " ".join(args.prompt).strip()

    # Handle subcommands: server, command, reload
    if prompt == "reload":
        sys.exit(_handle_server(["reload"]))

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
    print_help()
    sys.exit(0)
