"""Executes tool calls dispatched by the LLM."""

import subprocess

from rich.markdown import Markdown
from rich.padding import Padding

from sharkyo.display import console, print_info, print_error, print_success, prompt_user
from sharkyo.knowledge import KnowledgeManager
from sharkyo.rcfiles import load_rc, rc_int


def _run_cmd(args: dict) -> tuple[str | None, bool]:
    """Execute a shell command, return (output, should_continue)."""
    command = args.get("command", "")
    review_output = args.get("review_output", False)
    review_output_stderr = args.get("review_output_stderr", False)

    console.print(
        f"\n  [bold cyan]![/bold cyan] "
        f"Wants to run: [cyan]{command}[/cyan]"
    )
    if review_output:
        console.print("  [dim](output will be sent back to sharkyo)[/dim]")
    elif review_output_stderr:
        console.print("  [dim](stderr will be sent back to sharkyo if errors occur)[/dim]")

    confirm = prompt_user("Run it? (y/n):").strip().lower()
    if confirm not in ("y", "yes"):
        print_info("Cancelled.")
        return None, False

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        returncode = result.returncode
    except Exception as e:
        stdout = ""
        stderr = f"Error running command: {e}"
        returncode = 1

    # Format output for user display (always shown as codeblock)
    combined_parts = []
    if stdout:
        combined_parts.append(stdout)
    if stderr:
        combined_parts.append(stderr)
    combined = "\n".join(combined_parts).strip()
    raw = (combined or "(no output)").strip() + f" [ exit {returncode} ]"

    rc = load_rc()
    display_limit = rc_int(rc, "cmd_out_lines")
    lines = raw.splitlines()
    display_cut = len(lines) > display_limit
    visible = "\n".join(lines[:display_limit])
    if display_cut:
        visible += f"\n... ({len(lines) - display_limit} more lines)"

    codeblock = "```\n" + visible + "\n```"
    console.print(Padding(Markdown(codeblock), (0, 0, 0, 2)))

    # Determine what to review back to the model
    char_limit = rc_int(rc, "cmd_out_chars")

    if review_output:
        model_out = raw
        if len(model_out) > char_limit:
            model_out = model_out[:char_limit] + f"\n\n[Command output truncated: exceeded {char_limit} chars]"
        return model_out, True

    if review_output_stderr:
        err_content = stderr.strip()
        if err_content or returncode != 0:
            err_raw = (err_content or "(no stderr output)") + f" [ exit {returncode} ]"
            if len(err_raw) > char_limit:
                err_raw = err_raw[:char_limit] + f"\n\n[Stderr truncated: exceeded {char_limit} chars]"
            return err_raw, True
        else:
            return None, False

    return None, False



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
