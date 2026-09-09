# server/daemon.py
# Background daemon ("warm parent") that makes each `nux` invocation fast.

from __future__ import annotations

import os
import platform
import re
import signal
import socket
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from nux.server.defaults import PID_FILE, SOCKET_PATH
from nux.server.protocol import Packet, recv_message, send_message
from nux.ui.spinner import SpinnerHandle

if TYPE_CHECKING:
    from nux.core.config import Config

VERSION_MISMATCH_EXIT = -2


# run command for environmental context
def _run_cmd(cmd: str, args: list[str] | None = None) -> str:
    if args is None:
        args = []

    try:
        return (
            subprocess.check_output([cmd] + args, stderr=subprocess.DEVNULL, timeout=0.2)
            .decode("utf-8")
            .strip()
        )
    except (subprocess.SubprocessError, OSError):
        return ""


@dataclass
class Session:
    config: Config
    packet: Packet
    spinner: SpinnerHandle = field(default_factory=SpinnerHandle, compare=False)
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    timeout: int | None = None
    max_turns: int | None = None
    no_confirm: bool = False
    allowed_tools: list[str] | None = None

    @classmethod
    def create(cls, prompt: str, cwd: str | None = None, packet: Packet | None = None, flags: dict | None = None) -> Session:
        from nux.core.config import auto_adjust_config, load_config
        from nux.storage.apikeys import active_key

        config = load_config()

        # Auto-adjust token limits from model's context_window
        key = active_key()
        if key:
            config = auto_adjust_config(config, key.key, key.base_url)

        if packet is None:
            from nux import __version__

            packet = Packet(
                type="CLIENT",
                version=__version__,
                cwd=cwd or os.getcwd(),
                message={"prompt": prompt},
            )

        tools_str = (flags or {}).get("tools")
        allowed_tools = tools_str.split(",") if tools_str else None

        return cls(
            config=config,
            packet=packet,
            verbose=flags.get("verbose", False) if flags else False,
            quiet=flags.get("quiet", False) if flags else False,
            dry_run=flags.get("dry_run", False) if flags else False,
            timeout=flags.get("timeout") if flags else None,
            max_turns=flags.get("max_turns") if flags else None,
            no_confirm=flags.get("no_confirm", False) if flags else False,
            allowed_tools=allowed_tools,
        )

    def get_environment_context(self) -> str:
        cwd = self.packet.cwd or os.getcwd()
        git_remote = _run_cmd("git", ["config", "--get", "remote.origin.url"])
        git_branch = _run_cmd("git", ["branch", "--show-current"])

        system_platform = platform.system().lower()
        uname_info = _run_cmd("uname", ["-a"])

        if "darwin" in system_platform:  # macOS
            sw_vers_raw = _run_cmd("sw_vers", [])
            version_match = re.search(r"ProductVersion:\s*(.*)", sw_vers_raw)
            version = version_match.group(1).strip() if version_match else "Unknown version"
            os_name_version = f"macOS {version}"
        else:  # Linux
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read()
                pretty_name_match = re.search(r'^PRETTY_NAME=["\']?(.*?)["\']?$', content, re.MULTILINE)
                os_name_version = pretty_name_match.group(1) if pretty_name_match else "Linux"
            else:
                os_name_version = "Linux (Unknown Distro)"

        os_info = f"{os_name_version} | {uname_info}".strip()

        lines = [
            f"OS Information:\n {os_info}\n\n",
            f"Working Directory: {cwd}",
            f"Current Time: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
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
    from nux import __version__

    send_message(conn, Packet(type="SERVER", version=__version__, cwd="", message=message))


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
        from nux.core.agent import Agent
        from nux.core.error_logger import log_error
        from nux.core.errors import NuxError

        flags = {
            "verbose": packet.message.get("verbose", False),
            "quiet": packet.message.get("quiet", False),
            "dry_run": packet.message.get("dry_run", False),
            "timeout": packet.message.get("timeout"),
            "max_turns": packet.message.get("max_turns"),
            "no_confirm": packet.message.get("no_confirm", False),
            "tools": packet.message.get("tools"),
        }

        try:
            session = Session.create(prompt=prompt, packet=packet, flags=flags)
            agent = Agent(session)
            agent.run(prompt)

            if packet.message.get("json_output"):
                import json as _json

                output = {
                    "reply": agent.last_reply,
                    "model": session.config.model,
                    "dry_run": session.dry_run,
                }
                from nux.ui.display import console

                console.print(_json.dumps(output, ensure_ascii=False))

        except NuxError as e:
            log_error(e, context=f"prompt={prompt!r}")
            from nux.ui.display import print_error

            print_error(str(e))
            code = 1
    except KeyboardInterrupt:
        code = 130
    except Exception as e:  # noqa: BLE001 - report anything unexpected to the caller.
        log_error(e, context=f"prompt={prompt!r}")
        try:
            from nux.ui.display import print_error

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
    import nux.core.agent
    import nux.core.request_manager  # noqa: F401


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

    from nux import __version__

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
    from nux.core.constants import setup_dirs

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
