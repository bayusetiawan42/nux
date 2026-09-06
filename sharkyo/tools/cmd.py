"""Shell command execution tool."""

import os
import pty
import subprocess

import questionary
from rich.markdown import Markdown
from rich.padding import Padding

from sharkyo.config import Config
from sharkyo.display import console, print_info

SCHEMA = {
    "type": "function",
    "function": {
        "name": "CMD",
        "description": (
            "Run a shell command on the user's machine. "
            "Output is always shown to the user as a codeblock. "
            "Use review_output=true if you need to see stdout+stderr to give a follow-up reply. "
            "Use review_output_stderr=true if you only need stderr (e.g. to diagnose errors). "
            "Leave both false if you don't need to see the output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "review_output": {
                    "type": "boolean",
                    "description": (
                        "Send full stdout+stderr back to you for a follow-up reply. "
                        "Default: false."
                    ),
                },
                "review_output_stderr": {
                    "type": "boolean",
                    "description": (
                        "Send only stderr back to you for a follow-up reply. "
                        "Useful for checking if a command produced errors. "
                        "Default: false."
                    ),
                },
                "interactive": {
                    "type": "boolean",
                    "description": (
                        "Set true for commands that may prompt for input "
                        "(sudo, gh auth login, git credential prompts, npm init, etc). "
                        "Input is forwarded to the user's terminal via a pty. "
                        "Default: false."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}


def _run_interactive(command: str) -> tuple[str, str, int]:
    """Run command in a pty so stdin/stdout passthrough to the real terminal,
    while still capturing a transcript for later review."""
    buf = bytearray()

    def master_read(fd):
        data = os.read(fd, 1024)
        buf.extend(data)
        return data  # must return so pty.spawn still echoes it to real stdout

    argv = ["/bin/sh", "-c", command]
    status = pty.spawn(argv, master_read)
    if hasattr(os, "waitstatus_to_exitcode"):
        returncode = os.waitstatus_to_exitcode(status)
    else:
        returncode = status

    text = buf.decode(errors="replace")
    # pty merges stdout+stderr into one stream, so we report it all as stdout
    return text, "", returncode


def execute(args: dict, config: Config) -> tuple[str | None, bool]:
    """Execute a shell command with user confirmation and formatted display."""
    command = args.get("command", "")
    review_output = args.get("review_output", False)
    review_output_stderr = args.get("review_output_stderr", False)
    interactive = args.get("interactive", False)

    console.print(f"\n  [bold cyan]![/bold cyan] Wants to run: [cyan]{command}[/cyan]")
    if interactive:
        console.print("  [dim](interactive — respond to prompts in your terminal)[/dim]")
    if review_output:
        console.print("  [dim](output will be sent back to sharkyo)[/dim]")
    elif review_output_stderr:
        console.print("  [dim](stderr will be sent back to sharkyo if errors occur)[/dim]")

    confirm = questionary.select(
        "Run it?",
        choices=["Yes", "No"],
        style=questionary.Style([
            ("qmark", "fg:#00bcd4 bold"),
            ("question", "bold"),
            ("pointer", "fg:#00bcd4 bold"),
            ("highlighted", "fg:#00bcd4 bold"),
            ("selected", "fg:#00bcd4"),
        ]),
    ).ask()

    if confirm != "Yes":
        print_info("Cancelled.")
        return None, False

    if interactive:
        try:
            stdout, stderr, returncode = _run_interactive(command)
        except Exception as e:
            stdout, stderr, returncode = "", f"Error running command: {e}", 1
    else:
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

    display_limit = config.cmd_out_lines
    lines = raw.splitlines()
    display_cut = len(lines) > display_limit
    visible = "\n".join(lines[:display_limit])
    if display_cut:
        visible += f"\n... ({len(lines) - display_limit} more lines)"

    if interactive:
        # Already streamed live to the real terminal via the pty; don't reprint.
        console.print()
    else:
        codeblock = "```\n" + visible + "\n```"
        console.print(Padding(Markdown(codeblock), (0, 0, 0, 2)))

    # Determine what to review back to the model
    char_limit = config.cmd_out_chars

    if review_output:
        model_out = raw
        if len(model_out) > char_limit:
            head_chars = char_limit // 3
            tail_chars = char_limit - head_chars
            head = model_out[:head_chars]
            tail = model_out[-tail_chars:]
            model_out = f"{head}\n\n[... output truncated ...]\n\n{tail}"
        return model_out, True

    if review_output_stderr:
        err_content = stderr.strip()
        if err_content or returncode != 0:
            err_raw = (err_content or "(no stderr output)") + f" [ exit {returncode} ]"
            if len(err_raw) > char_limit:
                head_chars = char_limit // 3
                tail_chars = char_limit - head_chars
                err_raw = f"{err_raw[:head_chars]}\n\n[... stderr truncated ...]\n\n{err_raw[-tail_chars:]}"
            return err_raw, True
        return None, False

    return None, False
