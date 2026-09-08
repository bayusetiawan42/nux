# server/client.py
# Thin client for the Sharkyo background daemon.

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time

from sharkyo import __version__
from sharkyo.server.daemon import VERSION_MISMATCH_EXIT, running
from sharkyo.server.defaults import SOCKET_PATH, STARTUP_WAIT
from sharkyo.server.protocol import Packet, recv_message, send_message


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
    from sharkyo.core.constants import setup_dirs

    setup_dirs()
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


def _send_request(prompt: str) -> tuple[Packet, int | None]:
    conn = _connect()
    if conn is None:
        return None, None  # type: ignore[return-value]

    packet = Packet(
        type="CLIENT",
        version=__version__,
        cwd=os.getcwd(),
        env=dict(os.environ),
        message={"prompt": prompt},
    )

    try:
        send_message(conn, packet)
        pid_packet, _ = recv_message(conn)
        child_pid = pid_packet.message.get("pid")
        return pid_packet, child_pid
    except OSError:
        return None, None  # type: ignore[return-value]


def run_remote(prompt: str) -> int | None:
    if not running():
        start_daemon()
        deadline = time.monotonic() + STARTUP_WAIT
        while time.monotonic() < deadline:
            if _connect() is not None:
                break
            time.sleep(0.1)
        else:
            return None

    conn = _connect()
    if conn is None:
        return None

    try:
        packet = Packet(
            type="CLIENT",
            version=__version__,
            cwd=os.getcwd(),
            env=dict(os.environ),
            message={"prompt": prompt},
        )
        send_message(conn, packet)

        pid_packet, _ = recv_message(conn)
        child_pid = pid_packet.message.get("pid")
        if child_pid is None:
            return None

        prev = signal.signal(signal.SIGINT, _make_sigint_handler(child_pid))
        try:
            exit_packet, _ = recv_message(conn)
            code = exit_packet.message.get("exit_code")
            if code == VERSION_MISMATCH_EXIT:
                return _retry(prompt)
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


def _retry(prompt: str) -> int | None:
    from sharkyo.server.daemon import stop

    stop()
    start_daemon()
    deadline = time.monotonic() + STARTUP_WAIT
    while time.monotonic() < deadline:
        if _connect() is not None:
            break
        time.sleep(0.1)
    else:
        return None

    conn = _connect()
    if conn is None:
        return None

    try:
        packet = Packet(
            type="CLIENT",
            version=__version__,
            cwd=os.getcwd(),
            env=dict(os.environ),
            message={"prompt": prompt},
        )
        send_message(conn, packet)

        pid_packet, _ = recv_message(conn)
        child_pid = pid_packet.message.get("pid")
        if child_pid is None:
            return None

        prev = signal.signal(signal.SIGINT, _make_sigint_handler(child_pid))
        try:
            exit_packet, _ = recv_message(conn)
            return exit_packet.message.get("exit_code")
        finally:
            signal.signal(signal.SIGINT, prev)
    except OSError:
        return None
    finally:
        try:
            conn.close()
        except OSError:
            pass
