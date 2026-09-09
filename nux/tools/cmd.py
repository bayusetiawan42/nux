# tools/cmd.py
# Shell command execution tool using pty for streaming output and input support.

from __future__ import annotations

import codecs
import fcntl
import io
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import questionary
from rich.markdown import Markdown

from nux.core.utils.helper import token_len
from nux.tools import register_tool
from nux.tools.result import ToolResult
from nux.ui.display import (
    QUESTIONARY_STYLE_SPEC,
    console,
    is_interactive,
    print_error,
    print_info,
)

if TYPE_CHECKING:
    from nux.server.daemon import Session

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


def _get_stdin_fd() -> int | None:
    # Safely get stdin file descriptor. Returns None if stdin is not a real TTY
    # (e.g., in pytest, daemon mode, or non-interactive environments).
    try:
        fd = sys.stdin.fileno()
        if fd < 0:
            return None
        return fd
    except (io.UnsupportedOperation, ValueError, OSError):
        return None


def _configure_terminal(pty_fd: int) -> None:
    # Configure pty slave terminal for clean streaming output.
    # ONLCR:  NL -> CR-NL  (disable to prevent doubled newlines)
    # ECHOCTL: echo control chars like ^C ^D (disable to prevent garbled output)
    try:
        term_settings = termios.tcgetattr(pty_fd)
        term_settings[1] &= ~termios.ONLCR
        term_settings[3] &= ~termios.ECHOCTL
        termios.tcsetattr(pty_fd, termios.TCSANOW, term_settings)
    except termios.error:
        pass


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    # Set the terminal window size for the pty slave so that commands
    # like top, htop, and bash prompts render correctly.
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


def _get_terminal_size() -> tuple[int, int]:
    # Get the current terminal size, fallback to 24x80.
    try:
        size = os.get_terminal_size()
        return size.lines, size.columns
    except OSError:
        return 24, 80


def _run(
    command: str,
    config: object,
    pass_output_to_user: bool = True,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[str, int]:
    # Create a pseudo-terminal pair. The slave end is given to the child
    # process as its stdin/stdout/stderr, and the parent monitors the master
    # end for output while forwarding user stdin input.
    parent_pty, child_pty = pty.openpty()
    _configure_terminal(child_pty)
    rows, cols = _get_terminal_size()
    _set_winsize(child_pty, rows, cols)

    proc = subprocess.Popen(
        command,
        shell=True,
        stdin=child_pty,
        stdout=child_pty,
        stderr=child_pty,
        close_fds=True,
        cwd=cwd,
        env=env,
    )
    # The slave is only needed by the child; parent closes it.
    os.close(child_pty)

    # Set the master to non-blocking so reads don't hang.
    flags = fcntl.fcntl(parent_pty, fcntl.F_GETFL)
    fcntl.fcntl(parent_pty, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    printed_chars: int = 0
    chunks: list[bytes] = []
    stdin_fd = _get_stdin_fd()

    try:
        while True:
            # Check if process has already terminated.
            ret = proc.poll()

            # Build the list of file descriptors to monitor.
            read_fds = [parent_pty]
            if stdin_fd is not None and ret is None:
                read_fds.append(stdin_fd)

            # Wait for I/O availability.
            readable, _, _ = select.select(read_fds, [], [], 0.05)

            # Read command output from the pty master.
            if parent_pty in readable:
                try:
                    data = os.read(parent_pty, 4096)
                except OSError:
                    data = b""
                if not data:
                    # EOF on the pty master means the child closed its end.
                    # If the process is already dead, we are done.
                    if ret is not None:
                        break
                    # Otherwise briefly sleep and re-check.
                    continue

                chunks.append(data)

                if pass_output_to_user and printed_chars < config.max_command_output_display:
                    text = decoder.decode(data, final=False)
                    rem_chars = max(0, config.max_command_output_display - printed_chars)
                    sys.stdout.buffer.write(text[:rem_chars].encode("utf-8", errors="replace"))
                    sys.stdout.flush()
                    printed_chars += len(text)

            # Forward user stdin to the command's pty.
            if stdin_fd is not None and stdin_fd in readable:
                try:
                    data = os.read(stdin_fd, 4096)
                    if data:
                        os.write(parent_pty, data)
                    else:
                        stdin_fd = None
                except OSError:
                    stdin_fd = None

            # If the process exited and the pty has no more data, we are done.
            if ret is not None and not readable:
                # Give the pty a moment to flush any buffered output.
                time.sleep(0.05)
                try:
                    data = os.read(parent_pty, 4096)
                    if data:
                        chunks.append(data)
                        if (
                            pass_output_to_user
                            and printed_chars < config.max_command_output_display
                        ):
                            text = decoder.decode(data, final=False)
                            rem_chars = max(0, config.max_command_output_display - printed_chars)
                            sys.stdout.buffer.write(
                                text[:rem_chars].encode("utf-8", errors="replace")
                            )
                            sys.stdout.flush()
                            printed_chars += len(text)
                except OSError:
                    pass
                break

    except KeyboardInterrupt:
        try:
            proc.kill()
        except OSError:
            pass
        raise
    finally:
        os.close(parent_pty)

    # Flush any remaining bytes in the incremental decoder.
    remainder = decoder.decode(b"", final=True)
    if remainder:
        chunks.append(remainder.encode("utf-8", errors="replace"))

    transcript = b"".join(chunks).decode(errors="replace")
    return transcript, proc.returncode


@register_tool("CMD")
def execute(args: dict, session: Session) -> ToolResult:
    parsed = CmdArgs.from_dict(args)

    console.print(Markdown(f"```bash\n$ {parsed.command}\n```"))

    cancelled = False
    if session.no_confirm:
        pass
    elif is_interactive():
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
        return ToolResult(output="Command cancelled by user.", should_continue=False)

    sys.stdout.flush()

    try:
        transcript, returncode = _run(
            parsed.command,
            session.config,
            parsed.pass_output_to_user,
            cwd=session.packet.cwd,
        )
    except KeyboardInterrupt:
        print_info("Command interrupted.")
        return ToolResult(output="Command interrupted by user.", should_continue=False)

    if sys.stdout.isatty() and returncode != 0:
        print_error(f"\nCommand exited with code {returncode}.")

    if token_len(transcript) > session.config.max_command_output_tokens:
        transcript = (
            transcript[: session.config.max_command_output_tokens] + "[ ... Output truncated ... ]"
        )

    output = f"{transcript}\n[ exit code: {returncode} ]"
    return ToolResult(output=output, should_continue=not parsed.stop_after_execution)
