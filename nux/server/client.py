# server/client.py
# Thin client for the Nux background daemon.

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time

from nux import __version__
from nux.server.daemon import VERSION_MISMATCH_EXIT, running
from nux.server.defaults import SOCKET_PATH, STARTUP_WAIT
from nux.server.protocol import Packet, recv_message, send_message


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
    from nux.core.constants import setup_dirs

    setup_dirs()
    with open(os.devnull, "r+b") as devnull:
        subprocess.Popen(
            [sys.executable, "-m", "nux.server.daemon"],
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


def _wait_for_daemon(deadline: float) -> bool:
    while time.monotonic() < deadline:
        if _connect() is not None:
            return True
        time.sleep(0.1)
    return False


# Send prompt to daemon, return (exit_code, should_retry).
def _send_and_wait(prompt: str, flags: dict | None = None) -> tuple[int | None, bool]:
    conn = _connect()
    if conn is None:
        return None, False

    try:
        message: dict = {"prompt": prompt}
        if flags:
            message.update(flags)

        packet = Packet(
            type="CLIENT",
            version=__version__,
            cwd=os.getcwd(),
            message=message,
        )
        send_message(conn, packet)

        pid_packet, _ = recv_message(conn)
        child_pid = pid_packet.message.get("pid")
        if child_pid is None:
            return None, False

        prev = signal.signal(signal.SIGINT, _make_sigint_handler(child_pid))
        try:
            exit_packet, _ = recv_message(conn)
            code = exit_packet.message.get("exit_code")
            if code == VERSION_MISMATCH_EXIT:
                return code, True
            return code, False
        finally:
            signal.signal(signal.SIGINT, prev)
    except OSError:
        return None, False
    finally:
        try:
            conn.close()
        except OSError:
            pass


def run_remote(prompt: str, flags: dict | None = None) -> int | None:
    if not running():
        start_daemon()
        if not _wait_for_daemon(time.monotonic() + STARTUP_WAIT):
            return None

    code, should_retry = _send_and_wait(prompt, flags)

    if should_retry:
        from nux.server.daemon import stop

        stop()
        start_daemon()
        if not _wait_for_daemon(time.monotonic() + STARTUP_WAIT):
            return None
        code, _ = _send_and_wait(prompt, flags)

    return code
