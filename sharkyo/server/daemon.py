# server/daemon.py
# Background daemon ("warm parent") that makes each `sharkyo` invocation fast.

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sharkyo.server.defaults import PID_FILE, SOCKET_PATH
from sharkyo.server.protocol import Packet, recv_message, send_message

VERSION_MISMATCH_EXIT = -2


def _run_git(args: list[str]) -> str:
    try:
        return (
            subprocess.check_output(
                ["git"] + args,
                stderr=subprocess.DEVNULL,
                timeout=0.2,
            )
            .decode("utf-8")
            .strip()
        )
    except (subprocess.SubprocessError, OSError):
        return ""


@dataclass
class Session:
    config: object  # Config
    packet: Packet

    @classmethod
    def create(cls, prompt: str, cwd: str | None = None) -> Session:
        from sharkyo import __version__
        from sharkyo.core.config import load_config

        config = load_config()
        packet = Packet(
            type="CLIENT",
            version=__version__,
            cwd=cwd or os.getcwd(),
            env=dict(os.environ),
            message={"prompt": prompt},
        )
        return cls(config=config, packet=packet)

    def get_environment_context(self) -> str:
        cwd = self.packet.cwd or os.getcwd()
        git_remote = _run_git(["config", "--get", "remote.origin.url"])
        git_branch = _run_git(["branch", "--show-current"])

        lines = [
            f"Current Time: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Working Directory (CWD): {cwd}",
        ]

        if git_remote:
            lines.append(f"Git Remote (origin): {git_remote}")
        if git_branch:
            lines.append(f"Git Branch: {git_branch}")

        return "\n".join(lines)


_turn_runner: Callable[[Packet, int, int, int, socket.socket], None] | None = None


def register_turn_runner(
    runner: Callable[[Packet, int, int, int, socket.socket], None] | None,
) -> None:
    global _turn_runner
    _turn_runner = runner


def _send_server(conn: socket.socket, message: dict) -> None:
    from sharkyo import __version__

    send_message(conn, Packet(type="SERVER", version=__version__, cwd="", env={}, message=message))


def _default_turn_runner(
    packet: Packet, in_fd: int, out_fd: int, err_fd: int, conn: socket.socket
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

    if packet.cwd:
        try:
            os.chdir(packet.cwd)
        except OSError:
            pass

    _send_server(conn, {"pid": os.getpid()})

    prompt = packet.message.get("prompt", "")

    code = 0
    try:
        from sharkyo.core.agent import Agent
        from sharkyo.core.config import load_config
        from sharkyo.core.errors import SharkyoError

        try:
            session = Session(config=load_config(), packet=packet)
            Agent(session).run(prompt)
        except SharkyoError as e:
            from sharkyo.ui.display import print_error

            print_error(str(e))
            code = 1
    except KeyboardInterrupt:
        code = 130
    except Exception:  # noqa: BLE001 - report anything unexpected to the caller.
        try:
            import traceback

            from sharkyo.ui.display import print_error

            print_error(f"[dim]{traceback.format_exc()}[/dim]")
        except Exception:  # noqa: BLE001, S110 - last-resort error reporting
            pass
        code = 1

    _send_server(conn, {"exit_code": code})
    try:
        conn.close()
    except OSError:
        pass
    os._exit(0)


def _run_turn(packet: Packet, in_fd: int, out_fd: int, err_fd: int, conn: socket.socket) -> None:
    runner = _turn_runner or _default_turn_runner
    runner(packet, in_fd, out_fd, err_fd, conn)


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
        packet, fds = recv_message(conn)
    except OSError:
        try:
            conn.close()
        except OSError:
            pass
        return

    from sharkyo import __version__

    if packet.version != __version__:
        _send_server(conn, {"exit_code": VERSION_MISMATCH_EXIT})
        try:
            conn.close()
        except OSError:
            pass
        stop()
        return

    pid = os.fork()
    if pid == 0:
        _run_turn(packet, *fds, conn)
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
    from sharkyo.core.constants import setup_dirs

    setup_dirs()

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
