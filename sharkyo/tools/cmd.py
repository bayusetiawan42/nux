# tools/cmd.py
# Shell command execution tool.

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import questionary
from rich.markdown import Markdown
from rich.padding import Padding

from sharkyo.core.utils.helper import token_len
from sharkyo.tools import register_tool
from sharkyo.tools.result import ToolResult
from sharkyo.ui.display import QUESTIONARY_STYLE_SPEC, console, is_interactive, print_info

if TYPE_CHECKING:
    from sharkyo.server.daemon import Session

SCHEMA = {
    "type": "function",
    "function": {
        "name": "CMD",
        "description": (
            "Run a shell command on the user's machine. Output streams to the "
            "user's terminal live as it happens, and the full output is always "
            "sent back to you afterwards. "
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
                        "Keep as false if you wanna review the command output. "
                        "If true, stop the agent loop right after this command "
                        "finishes instead of continuing automatically. The "
                        "output is still sent back and recorded either way. "
                        "Default: false."
                    ),
                },
                "pass_output_to_user": {
                    "type": "boolean",
                    "description": (
                        "Set to false if command output might be too long"
                        "to be showed to the user. "
                        "If true, pass output to user so user can see what"
                        "this command output. Default: true."
                    ),
                },
            },
            "required": ["command", "pass_output_to_user"],
            "additionalProperties": False,
        },
    },
}

_CONFIRM_STYLE = questionary.Style(QUESTIONARY_STYLE_SPEC)


@dataclass
class CmdArgs:
    command: str
    pass_output_to_user: bool = False
    stop_after_execution: bool = False

    @classmethod
    def from_dict(cls, args: dict) -> CmdArgs:
        return cls(
            command=args.get("command", ""),
            stop_after_execution=args.get("stop_after_execution", False),
            pass_output_to_user=args.get("pass_output_to_user", True),
        )


def _run(
    command: str,
    config: object,
    pass_output_to_user: bool = True,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[str, int]:
    # stdin is ignored (no interactive prompts get forwarded); stdout+stderr
    # are merged and piped so we can stream them live while also collecting
    # the full, untruncated transcript to hand back to the agent.
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )

    printed_chars: int = 0
    chunks: list[bytes] = []

    assert proc.stdout is not None

    try:
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            chunks.append(chunk)

            if pass_output_to_user and printed_chars < config.max_command_output_display:
                chunk_text = chunk.decode(errors="replace")

                rem_chars = max(0, config.max_command_output_display - printed_chars)

                sys.stdout.buffer.write(chunk[:rem_chars])
                sys.stdout.flush()

                printed_chars += min(len(chunk_text), rem_chars)

    except KeyboardInterrupt:
        proc.terminate()
        raise
    finally:
        proc.wait()

    return b"".join(chunks).decode(errors="replace"), proc.returncode


@register_tool("CMD")
def execute(args: dict, session: Session) -> ToolResult:
    parsed = CmdArgs.from_dict(args)

    console.print(Markdown(f"```bash\n$ {parsed.command}\n```"))

    cancelled = False
    if is_interactive():
        confirm = questionary.select(
            "Run it?",
            choices=["Yes", "No"],
            style=_CONFIRM_STYLE,
        ).ask()

        cancelled = confirm != "Yes"
    else:
        console.print(
            "  [dim](warning: terminal is not interactive, running without confirmation)[/dim]"
        )

    if cancelled:
        print_info("Cancelled.")
        return ToolResult(output=None, should_continue=False)

    sys.stdout.flush()

    try:
        # Run command
        transcript, returncode = _run(
            parsed.command,
            session.config,
            parsed.pass_output_to_user,
            cwd=session.packet.cwd,
            env=session.packet.env,
        )

    except KeyboardInterrupt:
        print_info("Command interrupted.")
        return ToolResult(output="Command interrupted by user.", should_continue=False)

    if sys.stdout.isatty() and returncode != 0:
        console.print(f"\n  [red]![/red] Command exited with code {returncode}.")

    if token_len(transcript) > session.config.max_command_output_tokens:
        transcript = (
            transcript[: session.config.max_command_output_tokens] + "[ ... Output truncated ... ]"
        )

    output = f"{transcript}\n[ exit code: {returncode} ]"
    return ToolResult(output=output, should_continue=not parsed.stop_after_execution)
