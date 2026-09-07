# tools/cmd.py
# Shell command execution tool.

# TODO: remove interactive parameter, always use pty and create a output buffer
# useful for long-process commands

import os
import pty
import subprocess
from dataclasses import dataclass

import questionary
from rich.markdown import Markdown
from rich.padding import Padding

from sharkyo.config import Config
from sharkyo.display import console, print_info
from sharkyo.tools.result import ToolResult

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

_CONFIRM_STYLE = questionary.Style([
    ("qmark",       "fg:#00bcd4 bold"),
    ("question",    "bold"),
    ("pointer",     "fg:#00bcd4 bold"),
    ("highlighted", "fg:#00bcd4 bold"),
    ("selected",    "fg:#00bcd4"),
])


@dataclass
class CmdArgs:
    # Typed args for the CMD tool.
    command: str
    review_output: bool = False
    review_output_stderr: bool = False
    interactive: bool = False

    @classmethod
    def from_dict(cls, args: dict) -> "CmdArgs":
        return cls(
            command=args.get("command", ""),
            review_output=args.get("review_output", False),
            review_output_stderr=args.get("review_output_stderr", False),
            interactive=args.get("interactive", False),
        )


@dataclass
class _RunResult:
    # Internal result of a shell command execution.
    stdout: str
    stderr: str
    returncode: int


def _run_interactive(command: str) -> _RunResult:
    # Run a command via a pty so stdin/stdout pass through to the real terminal.
    # Captures a transcript of all output for optional model review.
    buf = bytearray()

    def master_read(fd: int) -> bytes:
        data = os.read(fd, 1024)
        buf.extend(data)
        # Must return data so pty.spawn echoes it to real stdout.
        return data

    argv = ["/bin/sh", "-c", command]
    status = pty.spawn(argv, master_read)
    if hasattr(os, "waitstatus_to_exitcode"):
        returncode = os.waitstatus_to_exitcode(status)
    else:
        returncode = status

    # pty merges stdout+stderr into one stream — report all as stdout.
    return _RunResult(stdout=buf.decode(errors="replace"), stderr="", returncode=returncode)


def _run_subprocess(command: str) -> _RunResult:
    # Run a command via subprocess with stdout/stderr captured separately.
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return _RunResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            returncode=result.returncode,
        )
    except Exception as e:
        return _RunResult(stdout="", stderr=f"Error running command: {e}", returncode=1)


def _truncate(text: str, char_limit: int, label: str = "output") -> str:
    # Truncate text to char_limit, keeping head and tail with a middle marker.
    if len(text) <= char_limit:
        return text
    head_chars = char_limit // 3
    tail_chars = char_limit - head_chars
    return f"{text[:head_chars]}\n\n[... {label} truncated ...]\n\n{text[-tail_chars:]}"


def execute(args: dict, config: Config) -> ToolResult:
    # Execute a shell command with user confirmation and formatted display.
    parsed = CmdArgs.from_dict(args)

    console.print(f"\n  [bold cyan]![/bold cyan] Wants to run: [cyan]{parsed.command}[/cyan]")
    if parsed.interactive:
        console.print("  [dim](interactive — respond to prompts in your terminal)[/dim]")
    if parsed.review_output:
        console.print("  [dim](output will be sent back to sharkyo)[/dim]")
    elif parsed.review_output_stderr:
        console.print("  [dim](stderr will be sent back to sharkyo if errors occur)[/dim]")

    confirm = questionary.select(
        "Run it?",
        choices=["Yes", "No"],
        style=_CONFIRM_STYLE,
    ).ask()

    if confirm != "Yes":
        print_info("Cancelled.")
        return ToolResult(output=None, should_continue=False)

    run_result = (
        _run_interactive(parsed.command)
        if parsed.interactive
        else _run_subprocess(parsed.command)
    )

    # Build the combined output string for display and optional model review.
    combined_parts = []
    if run_result.stdout:
        combined_parts.append(run_result.stdout)
    if run_result.stderr:
        combined_parts.append(run_result.stderr)
    combined = "\n".join(combined_parts).strip()
    raw = (combined or "(no output)").strip() + f" [ exit {run_result.returncode} ]"

    # Display to the user (always, capped to cmd_out_lines).
    if parsed.interactive:
        # Already streamed live to the terminal via pty — do not reprint.
        console.print()
    else:
        lines = raw.splitlines()
        visible_lines = lines[: config.cmd_out_lines]
        overflow = len(lines) - len(visible_lines)
        visible = "\n".join(visible_lines)
        if overflow > 0:
            visible += f"\n... ({overflow} more lines)"
        codeblock = "```\n" + visible + "\n```"
        console.print(Padding(Markdown(codeblock), (0, 0, 0, 2)))

    # Determine what (if anything) to send back to the model.
    if parsed.review_output:
        return ToolResult(
            output=_truncate(raw, config.cmd_out_chars),
            should_continue=True,
        )

    if parsed.review_output_stderr:
        err = run_result.stderr.strip()
        if err or run_result.returncode != 0:
            err_raw = (err or "(no stderr output)") + f" [ exit {run_result.returncode} ]"
            return ToolResult(
                output=_truncate(err_raw, config.cmd_out_chars, label="stderr"),
                should_continue=True,
            )
        return ToolResult(output=None, should_continue=False)

    return ToolResult(output=None, should_continue=False)
