# cli.py
# CLI argument parsing and handlers for Nux.

import os
import sys
import time
from dataclasses import dataclass

from nux.ui.display import console, print_error, print_info, print_success

AVAILABLE_COMMANDS = "clear, knowledge, clear-knowledge, delete-knowledge, server, reload, config, skills, logs, doctor"

_MSG_HISTORY_CLEARED = "History cleared."
_MSG_NO_KNOWLEDGE = "No knowledge stored yet."


@dataclass
class CliArgs:
    prompt: list[str]
    add_key: str | None = None
    base_url: str | None = None
    models: str | None = None  # None = flag only, str = key index
    stats: str | None = None  # None = no stats, "" = all keys, str = key index
    clear: bool = False
    knowledge: bool = False
    delete_knowledge: str | None = None
    clear_knowledge: bool = False
    version: bool = False
    no_color: bool = False
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    resume: bool = False
    sessions: bool = False
    json_output: bool = False
    timeout: int | None = None
    max_turns: int | None = None
    no_confirm: bool = False
    tools: str | None = None
    remove_key: str | None = None


_DESCRIPTION = "Nux. Your terminal on steroids!"

_COMMANDS = [
    ("nux <message>", "run a task"),
    ("nux server <start|stop|status|reload>", "manage the background daemon"),
    ("nux reload", "restart the background daemon"),
    ("nux command <name> [args]", "run a built-in command"),
    ("nux config [get|set|reset|path]", "view or modify configuration"),
    ("nux skills [search <query>]", "list or search available skills"),
    ("nux logs [clear]", "view or clear error logs"),
    ("nux doctor", "run diagnostics"),
]

_OPTIONS = [
    ("-v, --version", "show version and exit"),
    ("--add-key <key>", "add a Groq API key"),
    ("--remove-key <INDEX>", "remove an API key by index"),
    ("--base-url <url>", "set custom base URL for --add-key"),
    ("--models [KEY_INDEX]", "list available models for current or specific key"),
    ("--stats [KEY_INDEX]", "show keys, model, context window, and usage"),
    ("--keys", "show all keys (alias for --stats)"),
    ("--clear", "clear chat history"),
    ("--knowledge", "show stored persistent facts"),
    ("--delete-knowledge <key>", "delete a single knowledge entry"),
    ("--clear-knowledge", "wipe all stored knowledge"),
    ("--no-color", "disable colored output"),
    ("-V, --verbose", "show tool calls and intermediate steps"),
    ("-q, --quiet", "suppress all output except final reply"),
    ("-n, --dry-run", "show what the agent would do without executing"),
    ("-r, --resume", "resume the last conversation"),
    ("--sessions", "list past sessions"),
    ("--json", "output in JSON format"),
    ("--timeout <seconds>", "set execution timeout"),
    ("--max-turns <n>", "limit agentic loop iterations"),
    ("--no-confirm", "skip confirmation prompts for tool execution"),
    ("--tool <t1,t2>", "restrict agent to specific tools (comma-separated)"),
    ("-h, --help", "show this help message and exit"),
]

_EXAMPLES = [
    'nux "compress this folder"',
    "nux --clear --clear-knowledge",
    'nux --clear -- "Change this repo to private"',
    "nux command keys",
    "nux server status",
    "nux reload",
]


def _col_width(items: list[tuple[str, str]]) -> int:
    return max(len(syn) for syn, _ in items) + 2


def print_help() -> None:
    w = _col_width(_COMMANDS)
    print("Usage: nux [options] [message...]\n")
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

        if arg == "-v" or arg == "--version":
            from nux import __version__

            print(f"nux {__version__}")
            sys.exit(0)

        if arg == "--no-color":
            args.no_color = True
        elif arg == "-V" or arg == "--verbose":
            args.verbose = True
        elif arg == "-q" or arg == "--quiet":
            args.quiet = True
        elif arg == "-n" or arg == "--dry-run":
            args.dry_run = True
        elif arg == "-r" or arg == "--resume":
            args.resume = True
        elif arg == "--sessions":
            args.sessions = True
        elif arg == "--json":
            args.json_output = True
        elif arg == "--timeout":
            i += 1
            if i >= n:
                print_error("--timeout requires a value")
                sys.exit(1)
            try:
                args.timeout = int(argv[i])
            except ValueError:
                print_error("--timeout must be an integer (seconds)")
                sys.exit(1)
        elif arg == "--max-turns":
            i += 1
            if i >= n:
                print_error("--max-turns requires a value")
                sys.exit(1)
            try:
                args.max_turns = int(argv[i])
            except ValueError:
                print_error("--max-turns must be an integer")
                sys.exit(1)
        elif arg == "--no-confirm":
            args.no_confirm = True
        elif arg == "--tool":
            i += 1
            if i >= n:
                print_error("--tool requires a value")
                sys.exit(1)
            args.tools = argv[i]
        elif arg == "--remove-key":
            i += 1
            if i >= n:
                print_error("--remove-key requires a value")
                sys.exit(1)
            args.remove_key = argv[i]
        elif arg == "--add-key":
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
        elif arg == "--models" or arg.startswith("--models="):
            # --models alone, or --models=INDEX
            if "=" in arg:
                args.models = arg.split("=", 1)[1] or ""
            elif i + 1 < n and not argv[i + 1].startswith("-"):
                i += 1
                args.models = argv[i]
            else:
                args.models = ""
        elif arg == "--stats" or arg.startswith("--stats="):
            if "=" in arg:
                args.stats = arg.split("=", 1)[1] or ""
            elif i + 1 < n and not argv[i + 1].startswith("-"):
                i += 1
                args.stats = argv[i]
            else:
                args.stats = ""
        elif arg == "--keys":
            args.stats = ""
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


def _print_knowledge() -> None:
    from nux.tools.knowledge import list_all_formatted

    formatted = list_all_formatted()
    if not formatted:
        print_info(_MSG_NO_KNOWLEDGE)
        return
    console.print("[bold cyan]Stored knowledge:[/bold cyan]")
    for line in formatted.splitlines():
        key, _, value = line.partition("=")
        console.print(f"  [cyan]{key.strip()}[/cyan] = {value.strip()}")


def _print_models(key_index: str | None) -> None:
    from nux.storage.apikeys import active_key, list_keys

    keys = list_keys()
    if not keys:
        print_info("No API keys stored. Add one with: nux --add-key KEY")
        return

    from rich.table import Table

    from nux.core.llm import Groq

    if key_index:
        idx = int(key_index)
        match = [k for k in keys if k.id == idx]
        if not match:
            print_error(f"Key index {idx} not found. Use --stats to see available indices.")
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

    table = Table(title=None, box=None, padding=(0, 2, 0, 0))

    table.add_column("Model ID", style="dim", justify="left")
    table.add_column("Context Window", style="green", justify="right")
    table.add_column("Owned By", style="blue", justify="left")

    for m in models:
        ctx = getattr(m, "context_window", None)
        ctx_str = f"{ctx:,}" if ctx else "-"
        owner = getattr(m, "owned_by", "-")

        table.add_row(m.id, ctx_str, owner)

    console.print(table)


def _print_stats(key_index: str | None) -> None:
    import time as _time

    from rich.table import Table

    from nux.core.config import _fetch_context_window, load_config
    from nux.core.llm import Groq
    from nux.core.utils.helper import token_len
    from nux.storage.apikeys import active_key, list_keys
    from nux.storage.history import HistoryManager

    keys = list_keys()
    if not keys:
        print_info("No API keys stored. Add one with: nux --add-key KEY")
        return

    if key_index:
        idx = int(key_index)
        match = [k for k in keys if k.id == idx]
        if not match:
            print_error(f"Key index {idx} not found. Use --stats to see available indices.")
            return
        target_keys = [match[0]]
    else:
        target_keys = keys

    config = load_config()
    history = HistoryManager(config.max_history).load()
    history_tokens = sum(token_len(m.get("content") or "") for m in history)

    # Fetch owned_by from the API for the current model
    owner_map: dict[str, str] = {}
    try:
        ak = active_key() or keys[0]
        client = Groq()(api_key=ak.key, base_url=ak.base_url)
        for m in client.models.list().data:
            owner_map[m.id] = getattr(m, "owned_by", "-")
    except Exception:  # noqa: BLE001, S110
        pass

    now = int(_time.time())
    table = Table(box=None, padding=(0, 2, 0, 0))
    table.add_column("Key", style="dim", justify="left")
    table.add_column("Model", style="cyan", justify="left")
    table.add_column("Owned By", style="blue", justify="left")
    table.add_column("Context", style="green", justify="right")
    table.add_column("History", style="yellow", justify="right")
    table.add_column("Status", justify="left")

    for k in target_keys:
        ctx = _fetch_context_window(config.model, k.key, k.base_url)
        ctx_str = f"{ctx:,}" if ctx else "?"
        owner = owner_map.get(config.model, "-")
        hist_str = f"{len(history)} msgs / ~{history_tokens:,} tok"
        if k.active:
            status = "[green]current[/green]"
        elif k.reset_at > now:
            wait = k.reset_at - now
            status = f"[yellow]rate-limited ({wait}s)[/yellow]"
        else:
            status = "inactive"
        table.add_row(
            f"[{k.id}] {_mask_key(k.key)}",
            config.model,
            owner,
            ctx_str,
            hist_str,
            status,
        )

    console.print(table)


def _handle_server(argv: list[str] | None) -> int | None:
    sub = argv[0] if argv else "start"
    from nux.server import running, start_daemon, stop

    if sub == "status":
        if running():
            print_success("nux server is running.")
        else:
            print_info("nux server is not running.")
        return 0

    if sub == "stop":
        if stop():
            print_success("nux server stopped.")
        else:
            print_info("No nux server running.")
        return 0

    if sub == "start":
        if running():
            print_info("nux server is already running.")
            return 0
        start_daemon()
        for _ in range(40):
            if running():
                print_success("nux server started.")
                return 0
            time.sleep(0.1)
        print_info("nux server starting in the background...")
        return 0

    if sub == "reload":
        stop()
        start_daemon()
        for _ in range(40):
            if running():
                print_success("nux server reloaded.")
                return 0
            time.sleep(0.1)
        print_info("nux server reloading in the background...")
        return 0

    print_error(f"Unknown server command: {sub}")
    print_info("Usage: nux server <start|stop|status|reload>")
    return 1


def _handle_config(argv: list[str] | None) -> int | None:
    from nux.core.config import _DEFAULTS, RC_FILE, load_config

    sub = argv[0] if argv else "get"

    if sub == "get":
        if len(argv) > 1:
            key = argv[1].lower()
            cfg = load_config()
            if not hasattr(cfg, key):
                print_error(f"Unknown config key: {key}")
                print_info(f"Available keys: {', '.join(_DEFAULTS.keys())}")
                return 1
            val = getattr(cfg, key)
            print(f"{key} = {val}")
            return 0

        cfg = load_config()
        from rich.table import Table

        table = Table(box=None, padding=(0, 2, 0, 0))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Default", style="dim")
        for k, default in _DEFAULTS.items():
            current = getattr(cfg, k)
            marker = "" if current == default else " *"
            table.add_row(k, f"{current}{marker}", str(default))
        console.print(table)
        print_info("Values marked with * differ from defaults.")
        return 0

    if sub == "set":
        if len(argv) < 3:
            print_error("Usage: nux config set <key> <value>")
            return 1
        key = argv[1].lower()
        value = argv[2]
        if key not in _DEFAULTS:
            print_error(f"Unknown config key: {key}")
            print_info(f"Available keys: {', '.join(_DEFAULTS.keys())}")
            return 1

        target_type = type(_DEFAULTS[key])
        try:
            target_type(value)
        except (ValueError, TypeError):
            print_error(f"Invalid value for {key}: expected {target_type.__name__}")
            return 1

        lines: list[str] = []
        if os.path.exists(RC_FILE):
            with open(RC_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()

        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parsed_key = None
            if "=" in stripped:
                parsed_key = stripped.split("=", 1)[0].strip().lower()
            elif ":" in stripped:
                parsed_key = stripped.split(":", 1)[0].strip().lower()
            if parsed_key == key:
                lines[i] = f"{key} = {value}\n"
                found = True
                break

        if not found:
            lines.append(f"{key} = {value}\n")

        with open(RC_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print_success(f"Set {key} = {value}")
        return 0

    if sub == "reset":
        if os.path.exists(RC_FILE):
            os.remove(RC_FILE)
        print_success("Config reset to defaults.")
        return 0

    if sub == "path":
        print(f"Config:  {RC_FILE}")
        from nux.core.constants import DB_FILE, NUX_DIR, SKILLS_DIR
        from nux.core.error_logger import ERROR_DIR

        print(f"Data:    {NUX_DIR}")
        print(f"Database: {DB_FILE}")
        print(f"Skills:  {SKILLS_DIR}")
        print(f"Errors:  {ERROR_DIR}")
        return 0

    print_error(f"Unknown config command: {sub}")
    print_info("Usage: nux config [get|set|reset|path]")
    return 1


def _handle_skills(argv: list[str] | None) -> int | None:
    from nux.core.constants import SKILLS_DIR

    sub = argv[0] if argv else "list"

    if sub == "search":
        query = " ".join(argv[1:]) if len(argv) > 1 else ""
        if not query:
            print_error("Usage: nux skills search <query>")
            return 1
        from nux.search import BM25Searcher

        searcher = BM25Searcher(documents_dir=SKILLS_DIR)
        results = searcher.search(query, top_k=5)
        if not results:
            print_info(f"No skills found for: {query}")
            return 0
        from rich.table import Table

        table = Table(box=None, padding=(0, 2, 0, 0))
        table.add_column("Skill", style="cyan")
        table.add_column("Score", style="green", justify="right")
        for r in results:
            table.add_row(r.title, str(r.score))
        console.print(table)
        return 0

    if sub == "list" or sub == "":
        import glob as _glob

        pattern = os.path.join(SKILLS_DIR, "*.md")
        files = sorted(_glob.glob(pattern))
        if not files:
            print_info("No skills found.")
            return 0
        from rich.table import Table

        table = Table(box=None, padding=(0, 2, 0, 0))
        table.add_column("Skill", style="cyan")
        table.add_column("File", style="dim")
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            table.add_row(name, os.path.basename(f))
        console.print(table)
        return 0

    print_error(f"Unknown skills command: {sub}")
    print_info("Usage: nux skills [list|search <query>]")
    return 1


def _handle_sessions() -> int | None:
    from datetime import datetime, timezone

    from rich.table import Table

    from nux.storage.db import execute_read

    rows = execute_read(
        "SELECT role, content, created_at FROM history ORDER BY id"
    )
    if not rows:
        print_info("No sessions found.")
        return 0

    sessions: list[dict] = []
    current: list[dict] = []
    last_ts = 0
    gap = 1800  # 30 minutes

    for row in rows:
        ts = row["created_at"]
        if current and (ts - last_ts) > gap:
            sessions.append({"messages": current, "start": current[0]["created_at"]})
            current = []
        current.append(row)
        last_ts = ts

    if current:
        sessions.append({"messages": current, "start": current[0]["created_at"]})

    table = Table(box=None, padding=(0, 2, 0, 0))
    table.add_column("#", style="dim", justify="right")
    table.add_column("Started", style="cyan")
    table.add_column("Messages", style="green", justify="right")
    table.add_column("Preview", style="dim")

    for i, sess in enumerate(reversed(sessions), 1):
        start_dt = datetime.fromtimestamp(sess["start"], tz=timezone.utc)
        start_str = start_dt.strftime("%Y-%m-%d %H:%M")
        msg_count = len(sess["messages"])
        first_user = next(
            (m for m in sess["messages"] if m["role"] == "user"), None
        )
        preview = (first_user["content"] or "")[:50] if first_user else "-"
        table.add_row(str(i), start_str, str(msg_count), preview)

    console.print(table)
    print_info(f"{len(sessions)} session(s) found.")
    return 0


def _handle_logs(argv: list[str] | None) -> int | None:
    from nux.core.error_logger import ERROR_LOG

    sub = argv[0] if argv else "show"

    if sub == "clear":
        if os.path.exists(ERROR_LOG):
            os.remove(ERROR_LOG)
            print_success("Logs cleared.")
        else:
            print_info("No logs to clear.")
        return 0

    if sub == "show" or sub == "":
        if not os.path.exists(ERROR_LOG):
            print_info("No error logs found.")
            return 0
        with open(ERROR_LOG, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            print_info("Error log is empty.")
            return 0
        from rich.syntax import Syntax

        console.print(Syntax(content, "log", theme="monokai", line_numbers=False))
        return 0

    print_error(f"Unknown logs command: {sub}")
    print_info("Usage: nux logs [show|clear]")
    return 1


def _handle_doctor() -> int | None:
    from rich.table import Table

    table = Table(box=None, padding=(0, 2, 0, 0))
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="left")
    table.add_column("Detail", style="dim")

    from nux import __version__

    table.add_row("Version", "[green]OK[/green]", __version__)

    from nux.core.config import RC_FILE, load_config

    if os.path.exists(RC_FILE):
        try:
            load_config()
            table.add_row("Config", "[green]OK[/green]", RC_FILE)
        except Exception as e:  # noqa: BLE001
            table.add_row("Config", "[red]FAIL[/red]", str(e))
    else:
        table.add_row("Config", "[yellow]MISSING[/yellow]", f"Not found: {RC_FILE}")

    from nux.core.constants import DB_FILE

    if os.path.exists(DB_FILE):
        table.add_row("Database", "[green]OK[/green]", DB_FILE)
    else:
        table.add_row("Database", "[yellow]MISSING[/yellow]", f"Not found: {DB_FILE}")

    from nux.storage.apikeys import list_keys

    keys = list_keys()
    if keys:
        active = [k for k in keys if k.active]
        status = f"[green]OK[/green] ({len(keys)} keys, {len(active)} active)"
        table.add_row("API Keys", status, "")
    else:
        table.add_row("API Keys", "[red]NONE[/red]", "Add one with: nux --add-key KEY")

    from nux.server import running

    if running():
        table.add_row("Server", "[green]OK[/green]", "Daemon running")
    else:
        table.add_row("Server", "[yellow]STOPPED[/yellow]", "Not running (starts on demand)")

    import glob as _glob

    from nux.core.constants import SKILLS_DIR

    skill_count = len(_glob.glob(os.path.join(SKILLS_DIR, "*.md")))
    table.add_row("Skills", "[green]OK[/green]", f"{skill_count} skills loaded")

    try:
        import groq

        table.add_row("Groq SDK", "[green]OK[/green]", groq.__version__)
    except ImportError:
        table.add_row("Groq SDK", "[red]MISSING[/red]", "pip install groq")

    try:
        from importlib.metadata import version as _get_version

        rich_ver = _get_version("rich")
        table.add_row("Rich", "[green]OK[/green]", rich_ver)
    except Exception:  # noqa: BLE001
        table.add_row("Rich", "[red]MISSING[/red]", "pip install rich")

    console.print(table)
    return 0


def _handle_command(argv: list[str] | None) -> int | None:
    if not argv:
        print_info(f"Available commands: {AVAILABLE_COMMANDS}")
        print_info("Usage: nux command <name> [args]")
        return 0

    name = argv[0]
    cmd_args = argv[1:]

    if name == "clear":
        from nux.storage.history import HistoryManager

        HistoryManager().clear()
        print_success(_MSG_HISTORY_CLEARED)
        return 0

    if name == "knowledge":
        _print_knowledge()
        return 0

    if name == "clear-knowledge":
        from nux.tools.knowledge import clear_all

        clear_all()
        return 0

    if name == "delete-knowledge":
        from nux.tools.knowledge import delete_key

        if not cmd_args:
            print_error("Usage: nux command delete-knowledge <key>")
            return 1
        success, msg = delete_key(cmd_args[0])
        if success:
            print_success(msg)
        else:
            print_error(msg)
        return 0

    if name == "server":
        return _handle_server(cmd_args)

    if name == "config":
        return _handle_config(cmd_args)

    if name == "skills":
        return _handle_skills(cmd_args)

    if name == "logs":
        return _handle_logs(cmd_args)

    if name == "sessions":
        return _handle_sessions()

    if name == "doctor":
        return _handle_doctor()

    print_error(f"Unknown command: {name}")
    print_info(f"Available commands: {AVAILABLE_COMMANDS}")
    return 1


def main() -> str:
    args = parse()

    if args.no_color:
        from nux.ui.display import set_no_color

        set_no_color()

    # Run all flag-based actions (can combine multiple flags)
    ran_action = False

    if args.add_key:
        from nux.storage.apikeys import add_key

        add_key(args.add_key, base_url=args.base_url)
        print_success("API key added.")
        ran_action = True

    if args.remove_key:
        from nux.storage.apikeys import remove_key

        try:
            idx = int(args.remove_key)
        except ValueError:
            print_error("--remove-key must be a key index (integer)")
            sys.exit(1)
        success, msg = remove_key(idx)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        ran_action = True

    if args.models is not None:
        _print_models(args.models or None)
        ran_action = True

    if args.stats is not None:
        _print_stats(args.stats or None)
        ran_action = True

    if args.clear:
        from nux.storage.history import HistoryManager

        HistoryManager().clear()
        print_success(_MSG_HISTORY_CLEARED)
        ran_action = True

    if args.knowledge:
        _print_knowledge()
        ran_action = True

    if args.clear_knowledge:
        from nux.tools.knowledge import clear_all

        clear_all()
        ran_action = True

    if args.delete_knowledge:
        from nux.tools.knowledge import delete_key

        success, msg = delete_key(args.delete_knowledge)
        if success:
            print_success(msg)
        else:
            print_error(msg)
        ran_action = True

    if args.sessions:
        _handle_sessions()
        ran_action = True

    if args.resume and not args.prompt:
        from nux.storage.db import execute_read

        rows = execute_read(
            "SELECT role, content FROM history ORDER BY id DESC LIMIT 6",
        )
        if not rows:
            print_info("No history to resume.")
        else:
            print_info("Resuming from last conversation:")
            for row in reversed(rows):
                role = row["role"]
                content = row["content"] or ""
                if role == "user":
                    print_info(f"  you: {content[:100]}")
                elif role == "assistant":
                    print_info(f"  nux: {content[:100]}")
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

    if prompt.startswith("config ") or prompt == "config":
        parts = prompt.split(None, 1)
        sys.exit(_handle_config(parts[1].split() if len(parts) > 1 else []))

    if prompt.startswith("skills ") or prompt == "skills":
        parts = prompt.split(None, 1)
        sys.exit(_handle_skills(parts[1].split() if len(parts) > 1 else []))

    if prompt.startswith("logs ") or prompt == "logs":
        parts = prompt.split(None, 1)
        sys.exit(_handle_logs(parts[1].split() if len(parts) > 1 else []))

    if prompt == "sessions":
        sys.exit(_handle_sessions())

    if prompt == "doctor":
        sys.exit(_handle_doctor())

    # If we ran actions but there's no prompt, exit
    if ran_action and not prompt:
        sys.exit(0)

    # If there's a prompt, return it for the agent
    if prompt:
        return prompt

    # Nothing to do, show help
    print_help()
    sys.exit(0)


def get_flags() -> dict:
    args = parse()
    return {
        "verbose": args.verbose,
        "quiet": args.quiet,
        "no_color": args.no_color,
        "dry_run": args.dry_run,
        "resume": args.resume,
        "json_output": args.json_output,
        "timeout": args.timeout,
        "max_turns": args.max_turns,
        "no_confirm": args.no_confirm,
        "tools": args.tools,
    }
