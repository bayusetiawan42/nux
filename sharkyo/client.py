# client.py
# Thin client for the Sharkyo background daemon.
#
# Each `sharkyo "prompt"` call connects to the daemon socket, forwards the
# prompt plus its own stdin/stdout/stderr file descriptors, then waits for the
# daemon's forked child to finish. The child streams output and interactive
# prompts straight to the caller's terminal, so nothing needs to be echoed
# back over the socket — the client only relays the final exit code.
#
# If no daemon is running, the client starts one in the background and waits
# briefly for it to warm up, falling back to running in-process if the daemon
# cannot be brought up (e.g. fork is unavailable).

from __future__ import annotations

import array
import os
import signal
import socket
import struct
import subprocess
import sys
import time

from sharkyo.constants import SHARKYO_DIR
from sharkyo.server import SOCKET_PATH, STARTUP_WAIT, running


def _send_fds(conn: socket.socket) -> None:
    # Send our real stdin/stdout/stderr fds to the daemon via SCM_RIGHTS.
    fds = array.array("i", [0, 1, 2]).tobytes()
    conn.sendmsg(
        [b" "],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)],
    )


def _send_prompt(conn: socket.socket, prompt: str) -> None:
    # Send a length-prefixed prompt over the main (non-fd) path.
    data = prompt.encode("utf-8")
    conn.sendall(struct.pack("!I", len(data)) + data)


def _recv_int(conn: socket.socket) -> int | None:
    # Read a 4-byte big-endian int, tolerating EINTR (SIGINT wakeups).
    buf = b""
    while len(buf) < 4:
        try:
            chunk = conn.recv(4 - len(buf))
        except InterruptedError:
            continue
        if not chunk:
            return None
        buf += chunk
    return struct.unpack("!i", buf)[0]


def _connect(timeout: float = 2.0) -> socket.socket | None:
    # Try to connect to the daemon socket. Returns the connected socket, made
    # blocking again so the exit-code read can wait as long as the task runs.
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(timeout)
    try:
        conn.connect(SOCKET_PATH)
        conn.settimeout(None)
        return conn
    except OSError:
        conn.close()
        return None


def start_daemon() -> None:
    # Spawn a detached background daemon that preloads everything once.
    os.makedirs(SHARKYO_DIR, exist_ok=True)
    devnull = open(os.devnull, "r+b")
    subprocess.Popen(
        [sys.executable, "-m", "sharkyo.server"],
        stdin=devnull,
        stdout=devnull,
        stderr=devnull,
        start_new_session=True,
        close_fds=True,
    )


def _make_sigint_handler(child_pid: int):
    # Terminal Ctrl-C hits our process group. Forward it to the daemon child's
    # process group (the child told us its pid), which restores cancel fidelity
    # for running commands and the agent loop. We keep waiting for its report.
    def _forward(_signum: int, _frame: object) -> None:
        try:
            os.killpg(child_pid, signal.SIGINT)
        except OSError:
            pass

    return _forward


def run_remote(prompt: str) -> int | None:
    # Execute the prompt via the daemon. Returns the exit code, or None if the
    # daemon could not be reached after starting one up.
    if not running():
        start_daemon()
        deadline = time.monotonic() + STARTUP_WAIT
        while time.monotonic() < deadline:
            conn = _connect()
            if conn is not None:
                break
            time.sleep(0.1)
        else:  # timeout — daemon never came up
            return None
    else:
        conn = _connect()
        if conn is None:
            return None

    try:
        _send_prompt(conn, prompt)
        _send_fds(conn)
        # The child announces its pid first (so we can forward SIGINT to it),
        # then the final exit code once the turn completes.
        child_pid = _recv_int(conn)
        if child_pid is None:
            return None
        prev = signal.signal(signal.SIGINT, _make_sigint_handler(child_pid))
        try:
            code = _recv_int(conn)
            return code
        finally:
            signal.signal(signal.SIGINT, prev)
    except OSError:
        return None
    finally:
        try:
            conn.close()
        except OSError:
            pass