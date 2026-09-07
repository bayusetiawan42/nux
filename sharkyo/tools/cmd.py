# tools/cmd.py
# Shell command execution tool.

import subprocess
import sys
from dataclasses import dataclass

import questionary

from sharkyo.core.config import Config
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import QUESTIONARY_STYLE_SPEC, console, is_interactive, print_info

SCHEMA = {
    "type": "function",
    "function": {
        "name": "CMD",
        "description": (
            "Run a shell command on the user's machine. Output streams to the "
            "user's terminal live as it happens, and the full output is always "
            "sent back to you afterwards. "
            "Set stop_after_execution=true when you don't need to react to the "
            "result yourself (e.g. this was the last step) — the output is still "
            "recorded, but the agent loop stops instead of continuing "
            "automatically. Default: false."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "stop_after_execution": {
                    "type": "boolean",
                    "description": (
                        "If true, stop the agent loop right after this command "
                        "finishes instead of continuing automatically. The "
                        "output is still sent back and recorded either way. "
                        "Default: false."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}

_CONFIRM_STYLE = questionary.Style(QUESTIONARY_STYLE_SPEC)


@dataclass
class CmdArgs:
    command: str
    stop_after_execution: bool = False

    @classmethod
    def from_dict(cls, args: dict) -> "CmdArgs":
        return cls(
            command=args.get("command", ""),
            stop_after_execution=args.get("stop_after_execution", False),
        )


def _run(command: str) -> tuple[str, int]:
    # stdin is ignored (no interactive prompts get forwarded); stdout+stderr
    # are merged and piped so we can stream them live while also collecting
    # the full, untruncated transcript to hand back to the agent.
    proc = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    chunks: list[bytes] = []
    assert proc.stdout is not None
    try:
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            chunks.append(chunk)
            sys.stdout.buffer.write(chunk)
            sys.stdout.flush()
    except KeyboardInterrupt:
        proc.terminate()
        raise
    finally:
        proc.wait()

    return b"".join(chunks).decode(errors="replace"), proc.returncode


def execute(args: dict, config: Config) -> ToolResult:
    parsed = CmdArgs.from_dict(args)

    console.print(f"\n  [bold cyan]![/bold cyan] Wants to run: [cyan]{parsed.command}[/cyan]")

    cancelled = False
    if is_interactive():
        confirm = questionary.select(
            "Run it?",
            choices=["Yes", "No"],
            style=_CONFIRM_STYLE,
        ).ask()
        cancelled = confirm != "Yes"
    else:
        console.print("  [dim](non-interactive — running without confirmation)[/dim]")

    if cancelled:
        print_info("Cancelled.")
        return ToolResult(output=None, should_continue=False)

    sys.stdout.flush()

    try:
        transcript, returncode = _run(parsed.command)
    except KeyboardInterrupt:
        print_info("Command interrupted.")
        return ToolResult(output="Command interrupted by user.", should_continue=False)

    if sys.stdout.isatty() and returncode != 0:
        console.print(f"\n  [red]![/red] Command exited with code {returncode}.")

    output = f"{transcript}\n[ exit code: {returncode} ]"
    return ToolResult(output=output, should_continue=not parsed.stop_after_execution)
