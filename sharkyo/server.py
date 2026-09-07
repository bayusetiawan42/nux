# server.py
# Background daemon ("warm parent") that makes each `sharkyo` invocation fast.
#
# The daemon pre-imports the full Sharkyo + OpenAI stack once and holds a Unix
# socket in ~/.sharkyo/server.sock. Each invocation connects, hands over its
# prompt plus its own stdin/stdout/stderr file descriptors (SCM_RIGHTS), and
# the daemon forks a child that runs the agent. After a fork the child reuses
# the already-imported modules and already-initialized SQLite schema, so the
# per-call import/config/DB overhead collapses from ~1.9s to near zero while
# every interactive feature (CMD confirmation, live pty streaming, questionary,
# Ctrl-C) still runs against the caller's real terminal.
#
# Run it directly (`python -m sharkyo.server`) or via the `sharkyo server`
# command. The client auto-starts it on first use.

from __future__ import annotations

import array
import os
import signal
import socket
import struct
import sys
import time

from sharkyo.constants import SHARKYO_DIR

SOCKET_PATH = os.path.join(SHARKYO_DIR, "server.sock")
PID_FILE = os.path.join(SHARKYO_DIR, "server.pid")

# How long the client will wait for the daemon to finish warming up before
# giving up and running in-process.
STARTUP_WAIT = 8.0


# ---------------------------------------------------------------------------
# One-shot agent runner — runs in the forked child.
# ---------------------------------------------------------------------------
def _preload() -> None:
    # Pull in every heavy module so a forked child inherits them warm.
    import sharkyo.agent  # noqa: F401  (warms openai, tools, display, db)
    import sharkyo.request_manager  # noqa: F401


def _recv_exactly(conn: socket.socket, n: int) -> bytes:
    # Read exactly n bytes from the connection, or raise on EOF.
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise OSError("client closed connection while sending prompt")
        buf.extend(chunk)
    return bytes(buf)


def _recv_prompt(conn: socket.socket) -> str:
    # Read the length-prefixed prompt sent over the main (non-fd) path.
    (length,) = struct.unpack("!I", _recv_exactly(conn, 4))
    return _recv_exactly(conn, length).decode("utf-8")


def _recv_fds(conn: socket.socket, count: int = 3) -> list[int]:
    # Receive file descriptors via SCM_RIGHTS ancillary data.
    fds: list[int] = []
    spins = 0
    while len(fds) < count:
        _, ancdata, _, _ = conn.recvmsg(1, socket.CMSG_SPACE(max(count * 4, 4)))
        if not ancdata:
            # Control data not delivered yet (or purely a data-only message).
            spins += 1
            if spins > 100:
                raise OSError("no SCM_RIGHTS descriptors received")
            continue
        spins = 0
        for level, ctype, cdata in ancdata:
            if level == socket.SOL_SOCKET and ctype == socket.SCM_RIGHTS:
                fds.extend(int(fd) for fd in array.array("i", cdata[: count * 4]))
    return fds[:count]


def _run_turn(prompt: str, in_fd: int, out_fd: int, err_fd: int, conn: socket.socket) -> None:
    # Executed in the forked child. Swaps the inherited stdio for the caller's
    # real terminal fds, runs the agent, then reports the exit code.
    for target, src in ((0, in_fd), (1, out_fd), (2, err_fd)):
        try:
            os.dup2(src, target)
        except OSError:
            pass

    # Give ourselves our own process group so the client can forward terminal
    # SIGINT/Ctrl-C to exactly us (we are not in the caller's group or session).
    try:
        os.setpgid(0, 0)
    except OSError:
        pass

    # Tell the client our pid first, then run. It uses the pid to signal us.
    try:
        conn.sendall(struct.pack("!i", os.getpid()))
    except OSError:
        pass

    code = 0
    try:
        from sharkyo.config import load_config
        from sharkyo.request_manager import SharkyoError

        from sharkyo.agent import Agent

        prompt_text = prompt
        try:
            Agent(load_config()).run(prompt_text)
        except SharkyoError as e:
            from sharkyo.display import print_error

            print_error(str(e))
            code = 1
    except KeyboardInterrupt:
        code = 130
    except Exception as e:  # noqa: BLE001 - report anything unexpected to the caller.
        try:
            import traceback
            from sharkyo.display import print_error

            print_error(f"Unexpected error: {e}")
            traceback.print_exc()
        except Exception:  # noqa: BLE001
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


# ---------------------------------------------------------------------------
# Daemon lifecycle
# ---------------------------------------------------------------------------
def _remove_stale_socket() -> None:
    # Remove a leftover socket file if present (checked at start).
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass


def _socket_live() -> bool:
    # True if the socket file currently has a live daemon listening on it.
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
    # True if a daemon is reachable on the socket.
    return _socket_live()


def stop() -> bool:
    # Send SIGTERM to the running daemon and wait for it to clean up.
    # Returns True if a daemon was signalled.
    if not _socket_live():
        return False
    pid = _read_pid()
    if not pid:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    for _ in range(50):  # wait up to ~2.5s for the socket cleanup
        if not _socket_live():
            return True
        time.sleep(0.05)
    return True


def _serve(conn: socket.socket) -> None:
    # Handle a single connection: read the prompt + fds, fork a child to run it.
    try:
        prompt = _recv_prompt(conn)
        fds = _recv_fds(conn)
    except OSError:
        try:
            conn.close()
        except OSError:
            pass
        return

    pid = os.fork()
    if pid == 0:
        # Child: run the turn and exit. Never returns.
        _run_turn(prompt, *fds, conn)
    # Parent: discard our copies of the caller's fds and the connection and
    # keep serving. The child writes its exit code back on `conn`.
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
    # Main daemon loop: preload everything once, then accept and fork.
    os.makedirs(SHARKYO_DIR, exist_ok=True)

    # Single instance: never clobber a live daemon's socket. Only unlink when
    # the path is stale (nothing listening there).
    if _socket_live():
        return
    _remove_stale_socket()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(SOCKET_PATH)
    except OSError:
        # Another daemon bound the path between our check and bind.
        sock.close()
        return
    sock.listen(8)

    _preload()
    _write_pid()

    # Reap finished children so we never accumulate zombies.
    def _reap(_signum: object, _frame: object) -> None:
        while True:
            try:
                os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break

    # Graceful shutdown on SIGTERM/SIGINT: run the cleanup in `finally`.
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
    # Entry point for `python -m sharkyo.server`. Keeps the process in the
    # foreground so `sharkyo server start` can spawn it detached.
    run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
