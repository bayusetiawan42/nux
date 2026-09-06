"""Executes tool calls dispatched by the LLM."""

import subprocess

from sharkyo.display import print_info, print_error, print_success, prompt_user
from sharkyo.knowledge import KnowledgeManager
from sharkyo.rcfiles import load_rc, rc_int


def _run_cmd(args: dict) -> tuple[str, bool]:
    """Execute a shell command, return (output, should_continue)."""
    command = args.get("command", "")
    see_output = args.get("see_output", False)

    print_info(f"run: [bold]{command}[/bold]")
    confirm = prompt_user("Execute? [y/N] ").strip().lower()
    if confirm not in ("y", "yes"):
        print_info("Cancelled.")
        return "User cancelled the command.", False

    rc = load_rc()
    max_chars = rc_int(rc, "cmd_out_chars")
    max_lines = rc_int(rc, "cmd_out_lines")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        combined = (result.stdout + result.stderr).strip()
    except Exception as e:
        combined = f"Error running command: {e}"

    if not see_output:
        print_success(f"Done (exit {result.returncode})")
        return f"Command ran. Exit code: {result.returncode}", True

    # Truncate output
    lines = combined.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        combined = "\n".join(lines) + f"\n... (truncated to {max_lines} lines)"
    if len(combined) > max_chars:
        combined = combined[:max_chars] + f"\n... (truncated to {max_chars} chars)"

    print_success(f"Done (exit {result.returncode})")
    return combined or "(no output)", True


def _run_knowledge(args: dict) -> tuple[str, bool]:
    """Handle KNOWLEDGE tool operations, return (output, should_continue)."""
    op = args.get("op", "")
    key = args.get("key", "")
    value = args.get("value", "")
    km = KnowledgeManager()

    if op == "set":
        if not key or not value:
            return "Error: 'set' requires both key and value.", True
        km.set(key, value)
        print_success(f"Stored: {key} = {value}")
        return f"Stored: {key} = {value}", True

    elif op == "get":
        if not key:
            return "Error: 'get' requires a key.", True
        result = km.get(key)
        if result is None:
            return f"No knowledge found for key: {key}", True
        return f"{key} = {result}", True

    elif op == "list":
        entries = km.list_all()
        if not entries:
            return "No knowledge stored yet.", True
        lines = [f"{k} = {v}" for k, v in entries]
        return "\n".join(lines), True

    elif op == "delete":
        if not key:
            return "Error: 'delete' requires a key.", True
        deleted = km.delete(key)
        if deleted:
            print_success(f"Deleted knowledge key: {key}")
            return f"Deleted: {key}", True
        return f"Key not found: {key}", True

    else:
        return f"Unknown KNOWLEDGE op: {op}", True


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Dispatch tool by name. Returns (output, should_continue)."""
    if name == "CMD":
        return _run_cmd(args)
    elif name == "KNOWLEDGE":
        return _run_knowledge(args)
    else:
        print_error(f"Unknown tool: {name}")
        return f"Unknown tool: {name}", True
