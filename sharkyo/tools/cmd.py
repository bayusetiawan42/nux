# tools/cmd.py
# Shell command execution tool.
#
# Every command runs through a pseudo-terminal so output streams to the
# user live (long-running processes included), stdin can be forwarded to
# prompt-based commands, and a bounded transcript of the last
# `cmd_out_chars` bytes is kept for the model to review afterwards.

import os
import pty
import select
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass

import questionary

from sharkyo.config import Config
from sharkyo.display import QUESTIONARY_STYLE_SPEC, console, is_interactive, print_info
from sharkyo.tools.result import ToolResult

SCHEMA = {
    "type": "function",
    "function": {
        "name": "CMD",
        "description": (
            "Run a shell command on the user's machine. Output streams to the "
            "user's terminal live as it happens. "
            "Use review_output=true if you need to see the output (stdout+stderr "
            "merged, capped to the last few KB) to give a follow-up reply. "
            "Use review_output_stderr=true if you only need to know whether the "
            "command failed; the transcript is then sent back only when the exit "
            "code is non-zero. Leave both false if you don't need to see the output."
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
                        "Send the final tail of stdout+stderr back to you for a "
                        "follow-up reply. Default: false."
                    ),
                },
                "review_output_stderr": {
                    "type": "boolean",
                    "description": (
                        "Send the transcript back to you only when the command "
                        "fails (non-zero exit code). Useful for checking if a "
                        "command produced errors. Default: false."
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
    # Typed args for the CMD tool.
    command: str
    review_output: bool = False
    review_output_stderr: bool = False

    @classmethod
    def from_dict(cls, args: dict) -> "CmdArgs":
        return cls(
            command=args.get("command", ""),
            review_output=args.get("review_output", False),
            review_output_stderr=args.get("review_output_stderr", False),
        )


@dataclass
class _RunResult:
    # Result of a shell command execution.
    # `stdout` holds the merged pty transcript; stderr is not separable
    # through a pty and is always empty here.
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


class _Tail:
    # Bounded byte buffer that keeps only the most recent `limit` bytes.
    # Backed by a chunk deque so arbitrarily large outputs stay cheap.
    __slots__ = ("_parts", "_total", "limit")

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._parts: deque[bytes] = deque()
        self._total = 0

    def append(self, data: bytes) -> None:
        if not data or self.limit <= 0:
            return
        self._parts.append(data)
        self._total += len(data)
        while self._total > self.limit and self._parts:
            head = self._parts[0]
            if len(self._parts) == 1:
                # Single oversized chunk — keep only its tail slice.
                self._parts[0] = head[-self.limit:]
                self._total = min(len(head), self.limit)
                break
            overflow = self._total - self.limit
            if len(head) < overflow:
                self._total -= len(self._parts.popleft())
            else:
                self._parts[0] = head[overflow:]
                self._total -= overflow
                break

    def text(self) -> str:
        return b"".join(self._parts).decode(errors="replace")


def _exec_shell(command: str) -> int:
    # Exec the command inside the forked child. Never returns on success.
    try:
        os.execvp("sh", ["sh", "-c", command])
    except OSError:
        return 127
    return 0


def _terminate(pid: int) -> None:
    # Terminate the command's process group, escalating to SIGKILL.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            break
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            pass


def _run_pty(
    command: str,
    buf_limit: int,
    stream: bool = True,
    timeout: float = 0.0,
    forward_stdin: bool | None = None,
) -> _RunResult:
    # Run `command` through a pseudo-terminal.
    #
    # - Child output streams to the real stdout live (when stream=True) and
    #   the last buf_limit bytes are buffered as a transcript.
    # - Real stdin is forwarded to the child when forward_stdin is set
    #   (default: only when our stdin is a terminal, so prompt-based commands
    #   like sudo or gh auth login can be answered).
    # - SIGINT/SIGTERM/SIGHUP are forwarded to the child's process group so
    #   Ctrl-C cancels long-running commands.
    # - When timeout > 0, the command is killed after that many seconds.
    if forward_stdin is None:
        forward_stdin = sys.stdin.isatty()

    started = time.monotonic()
    pid, master_fd = pty.fork()
    if pid == 0:
        os._exit(_exec_shell(command))

    buf = _Tail(buf_limit)
    echo_fd = None
    if stream:
        try:
            echo_fd = sys.stdout.buffer.fileno()
        except (AttributeError, ValueError, OSError):
            echo_fd = None
    stdin_fd = sys.stdin.fileno() if forward_stdin else None

    prev_signals = {
        _sig: signal.getsignal(_sig)
        for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }

    def _forward(signum: int, frame: object) -> None:
        # Interrupt chars first (faithful Ctrl-C on the child's pty),
        # then the signal itself to the child process group.
        try:
            os.write(master_fd, b"\x03" if signum == signal.SIGINT else b"")
        except OSError:
            pass
        try:
            os.killpg(pid, signum)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    timed_out = False
    try:
        for sig in prev_signals:
            signal.signal(sig, _forward)

        while True:
            if timeout > 0:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    break
            else:
                remaining = 0.3

            rlist = [master_fd]
            if stdin_fd is not None:
                rlist.append(stdin_fd)
            try:
                r, _, _ = select.select(rlist, [], [], remaining)
            except InterruptedError:
                continue

            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf.append(data)
                if echo_fd is not None:
                    try:
                        os.write(echo_fd, data)
                    except OSError:
                        echo_fd = None

            if stdin_fd is not None and stdin_fd in r:
                try:
                    data = os.read(stdin_fd, 4096)
                except OSError:
                    stdin_fd = None
                    continue
                if not data:
                    stdin_fd = None
                    continue
                try:
                    os.write(master_fd, data)
                except OSError:
                    pass

        if timed_out:
            _terminate(pid)
        else:
            # Drain whatever is left after the child closed its end.
            while True:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf.append(data)
                if echo_fd is not None:
                    try:
                        os.write(echo_fd, data)
                    except OSError:
                        break
    finally:
        for sig, handler in prev_signals.items():
            signal.signal(sig, handler)
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            _, status = os.waitpid(pid, 0)
        except ChildProcessError:
            status = 0

    returncode = os.waitstatus_to_exitcode(status)
    transcript = buf.text()
    if timed_out:
        transcript += f"\n\n[... command timed out after {timeout:.0f}s ...]"
    return _RunResult(
        stdout=transcript,
        stderr="",
        returncode=returncode,
        timed_out=timed_out,
    )


def _truncate(text: str, char_limit: int, label: str = "output") -> str:
    # Truncate text to char_limit, keeping head and tail with a middle marker.
    if len(text) <= char_limit:
        return text
    head_chars = char_limit // 3
    tail_chars = char_limit - head_chars
    return f"{text[:head_chars]}\n\n[... {label} truncated ...]\n\n{text[-tail_chars:]}"


def execute(args: dict, config: Config) -> ToolResult:
    # Execute a shell command with user confirmation and live-streamed display.
    parsed = CmdArgs.from_dict(args)

    console.print(f"\n  [bold cyan]![/bold cyan] Wants to run: [cyan]{parsed.command}[/cyan]")
    if parsed.review_output:
        console.print("  [dim](output will be sent back to sharkyo)[/dim]")
    elif parsed.review_output_stderr:
        console.print("  [dim](will report if the command fails)[/dim]")

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

    # Ensure the confirmation text is on screen before the child's output
    # starts streaming through the raw file descriptor.
    sys.stdout.flush()

    result = _run_pty(parsed.command, buf_limit=config.cmd_out_chars, timeout=config.cmd_timeout)

    if sys.stdout.isatty():
        if result.timed_out:
            console.print(f"\n  [yellow]![/yellow] Command timed out after {config.cmd_timeout:.0f}s.")
        elif result.returncode not in (0,):
            console.print(f"\n  [red]![/red] Command exited with code {result.returncode}.")

    # Determine what (if anything) to send back to the model.
    if parsed.review_output:
        return ToolResult(
            output=_truncate(result.stdout, config.cmd_out_chars),
            should_continue=True,
        )

    if parsed.review_output_stderr:
        if result.returncode != 0:
            raw = (result.stdout or "(no output)") + f" [ exit {result.returncode} ]"
            return ToolResult(
                output=_truncate(raw, config.cmd_out_chars, label="stderr"),
                should_continue=True,
            )
        return ToolResult(output=None, should_continue=False)

    return ToolResult(output=None, should_continue=False)