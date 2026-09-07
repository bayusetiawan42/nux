# server/client.py
# Thin client for the Sharkyo background daemon.

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time

from sharkyo.server.daemon import running
from sharkyo.server.defaults import SOCKET_PATH, STARTUP_WAIT
from sharkyo.server.protocol import recv_int, send_fds, send_prompt


def _connect(timeout: float = 2.0) -> socket.socket | None:
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
    from sharkyo.core.constants import SHARKYO_DIR

    os.makedirs(SHARKYO_DIR, exist_ok=True)
    with open(os.devnull, "r+b") as devnull:
        subprocess.Popen(
            [sys.executable, "-m", "sharkyo.server.daemon"],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
            close_fds=True,
        )


def _make_sigint_handler(child_pid: int):
    def _forward(_signum: int, _frame: object) -> None:
        try:
            os.killpg(child_pid, signal.SIGINT)
        except OSError:
            pass

    return _forward


def run_remote(prompt: str) -> int | None:
    if not running():
        start_daemon()
        deadline = time.monotonic() + STARTUP_WAIT
        while time.monotonic() < deadline:
            conn = _connect()
            if conn is not None:
                break
            time.sleep(0.1)
        else:
            return None
    else:
        conn = _connect()
        if conn is None:
            return None

    try:
        send_prompt(conn, prompt)
        send_fds(conn)
        child_pid = recv_int(conn)
        if child_pid is None:
            return None
        prev = signal.signal(signal.SIGINT, _make_sigint_handler(child_pid))
        try:
            code = recv_int(conn)
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
