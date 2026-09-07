# server/daemon.py
# Background daemon ("warm parent") that makes each `sharkyo` invocation fast.

from __future__ import annotations

import os
import signal
import socket
import struct
import sys
import time
from collections.abc import Callable

from sharkyo.server.defaults import PID_FILE, SOCKET_PATH
from sharkyo.server.protocol import recv_fds, recv_prompt

_turn_runner: Callable[[str, int, int, int, socket.socket], None] | None = None


def register_turn_runner(runner: Callable[[str, int, int, int, socket.socket], None] | None) -> None:
    global _turn_runner
    _turn_runner = runner


def _default_turn_runner(
    prompt: str, in_fd: int, out_fd: int, err_fd: int, conn: socket.socket
) -> None:
    for target, src in ((0, in_fd), (1, out_fd), (2, err_fd)):
        try:
            os.dup2(src, target)
        except OSError:
            pass

    try:
        os.setpgid(0, 0)
    except OSError:
        pass

    try:
        conn.sendall(struct.pack("!i", os.getpid()))
    except OSError:
        pass

    code = 0
    try:
        from sharkyo.core.agent import Agent
        from sharkyo.core.config import load_config
        from sharkyo.core.errors import SharkyoError

        try:
            Agent(load_config()).run(prompt)
        except SharkyoError as e:
            from sharkyo.ui.display import print_error

            print_error(str(e))
            code = 1
    except KeyboardInterrupt:
        code = 130
    except Exception as e:  # noqa: BLE001 - report anything unexpected to the caller.
        try:
            import traceback

            from sharkyo.ui.display import print_error

            print_error(f"Unexpected error: {e}")
            traceback.print_exc()
        except Exception:  # noqa: BLE001, S110 - last-resort error reporting
            pass
        code = 1

    try:
        conn.sendall(struct.pack("!i", code))
    except OSError:
        pass
    try:
        conn.close()
    except OSError:
        pass
    os._exit(0)


def _run_turn(prompt: str, in_fd: int, out_fd: int, err_fd: int, conn: socket.socket) -> None:
    runner = _turn_runner or _default_turn_runner
    runner(prompt, in_fd, out_fd, err_fd, conn)


def _preload() -> None:
    import sharkyo.core.agent
    import sharkyo.core.request_manager  # noqa: F401


def _remove_stale_socket() -> None:
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass


def _socket_live() -> bool:
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.3)
    try:
        probe.connect(SOCKET_PATH)
        return True
    except OSError:
        return False
    finally:
        probe.close()


def _write_pid() -> None:
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def _read_pid() -> int | None:
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def running() -> bool:
    return _socket_live()


def stop() -> bool:
    if not _socket_live():
        return False
    pid = _read_pid()
    if not pid:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    for _ in range(50):
        if not _socket_live():
            return True
        time.sleep(0.05)
    return True


def _serve(conn: socket.socket) -> None:
    try:
        prompt = recv_prompt(conn)
        fds = recv_fds(conn)
    except OSError:
        try:
            conn.close()
        except OSError:
            pass
        return

    pid = os.fork()
    if pid == 0:
        _run_turn(prompt, *fds, conn)
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        conn.close()
    except OSError:
        pass


def run_forever() -> None:
    from sharkyo.core.constants import SHARKYO_DIR

    os.makedirs(SHARKYO_DIR, exist_ok=True)

    if _socket_live():
        return
    _remove_stale_socket()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(SOCKET_PATH)
    except OSError:
        sock.close()
        return
    sock.listen(8)

    _preload()
    _write_pid()

    def _reap(_signum: object, _frame: object) -> None:
        while True:
            try:
                os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break

    def _shutdown(_signum: object, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGCHLD, _reap)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            conn, _ = sock.accept()
            _serve(conn)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.close()
        except OSError:
            pass
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass
        try:
            os.unlink(PID_FILE)
        except OSError:
            pass


def main() -> int:
    run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
