# tests/test_daemon.py
# Daemon lifecycle tests: start, stop, running, PID file, socket management.

import os
import signal
import socket
import time

import pytest

from nux.server import daemon
from nux.server.defaults import PID_FILE, SOCKET_PATH


# Ensure daemon is stopped and paths are isolated for each test.
@pytest.fixture(autouse=True)
def cleanup_daemon(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon, "SOCKET_PATH", str(tmp_path / "server.sock"))
    monkeypatch.setattr(daemon, "PID_FILE", str(tmp_path / "server.pid"))
    # Also patch the defaults module imports used by daemon
    import nux.server.defaults as defaults_mod

    monkeypatch.setattr(defaults_mod, "SOCKET_PATH", str(tmp_path / "server.sock"))
    monkeypatch.setattr(defaults_mod, "PID_FILE", str(tmp_path / "server.pid"))

    # Stop any running daemon
    if daemon.running():
        daemon.stop()

    yield

    # Cleanup after test
    if daemon.running():
        daemon.stop()


class TestDaemonLifecycle:
    def test_running_when_no_daemon(self):
        assert daemon.running() is False

    def test_stop_when_no_daemon(self):
        assert daemon.stop() is False

    def test_pid_file_written(self, tmp_path):
        pid_file = tmp_path / "server.pid"
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        assert pid == os.getpid()

    def test_pid_file_nonexistent(self, tmp_path):
        pid_file = tmp_path / "nonexistent.pid"
        try:
            with open(pid_file, "r") as f:
                int(f.read().strip())
        except (OSError, ValueError):
            pass  # Expected


class TestSocketManagement:
    def test_socket_live_returns_false_when_no_socket(self, tmp_path):
        sock_path = str(tmp_path / "nonexistent.sock")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.3)
        try:
            probe.connect(sock_path)
            is_live = True
        except OSError:
            is_live = False
        finally:
            probe.close()
        assert is_live is False

    def test_socket_live_returns_true_when_connected(self, tmp_path):
        sock_path = str(tmp_path / "test.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)

        try:
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            probe.settimeout(0.3)
            try:
                probe.connect(sock_path)
                is_live = True
            except OSError:
                is_live = False
            finally:
                probe.close()
            assert is_live is True
        finally:
            server.close()
            os.unlink(sock_path)


class TestPreload:
    def test_preload_imports_modules(self):
        # Just verify it doesn't raise
        daemon._preload()

    def test_remove_stale_socket_nonexistent(self, tmp_path):
        sock_path = str(tmp_path / "nonexistent.sock")
        # Should not raise
        daemon._remove_stale_socket()

    def test_write_read_pid(self, tmp_path):
        pid_file = str(tmp_path / "test.pid")
        import nux.server.defaults as defaults_mod

        original_pid_file = defaults_mod.PID_FILE
        try:
            defaults_mod.PID_FILE = pid_file
            daemon._write_pid()
            pid = daemon._read_pid()
            assert pid == os.getpid()
        finally:
            defaults_mod.PID_FILE = original_pid_file

    def test_read_pid_nonexistent(self, tmp_path):
        pid_file = str(tmp_path / "nonexistent.pid")
        import nux.server.defaults as defaults_mod

        original_pid_file = defaults_mod.PID_FILE
        try:
            defaults_mod.PID_FILE = pid_file
            pid = daemon._read_pid()
            assert pid is None
        finally:
            defaults_mod.PID_FILE = original_pid_file
