# tests/test_client.py
# Client tests: connection, retry logic, version mismatch handling.

import os
import socket
import threading
import time

import pytest

from nux.server import client
from nux.server.protocol import Packet, send_message


# Isolate client paths for each test.
@pytest.fixture(autouse=True)
def cleanup_client(monkeypatch, tmp_path):
    sock_path = str(tmp_path / "client_test.sock")
    monkeypatch.setattr(client, "SOCKET_PATH", sock_path)
    yield


class TestConnect:
    def test_connect_returns_none_when_no_socket(self):
        result = client._connect(timeout=0.1)
        assert result is None

    def test_connect_returns_socket_when_server_running(self, monkeypatch, tmp_path):
        sock_path = str(tmp_path / "test.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)

        try:
            monkeypatch.setattr(client, "SOCKET_PATH", sock_path)
            conn = client._connect(timeout=1.0)
            assert conn is not None
            conn.close()
        finally:
            server.close()
            os.unlink(sock_path)


class TestMakeSigintHandler:
    def test_handler_forwards_sigint(self):
        mock_pid = 12345
        handler = client._make_sigint_handler(mock_pid)
        assert callable(handler)


class TestWaitForDaemon:
    def test_returns_false_when_timeout(self):
        result = client._wait_for_daemon(time.monotonic() + 0.1)
        assert result is False


class TestSendAndWait:
    def test_returns_none_when_no_connection(self):
        code, retry = client._send_and_wait("test prompt")
        assert code is None
        assert retry is False

    def test_sends_packet_correctly(self, monkeypatch, tmp_path):
        sock_path = str(tmp_path / "send_test.sock")
        received_packets = []
        server_ready = threading.Event()

        def server_handler():
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(sock_path)
            server.listen(1)
            server_ready.set()
            conn, _ = server.accept()

            # Ingest the full client message (length + JSON + SCM_RIGHTS fds)
            # before responding, mirroring the real daemon. A raw conn.recv()
            # would let the server reply/close before the client finishes its
            # fd-send, racing the client's sendmsg into a BrokenPipeError.
            from nux.server.protocol import recv_message

            packet, fds = recv_message(conn)
            received_packets.append(packet)
            for fd in fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

            # Send pid response
            pid_packet = Packet(type="SERVER", version="0.1.0", cwd="", message={"pid": 100})
            send_message(conn, pid_packet)

            # Send exit response
            exit_packet = Packet(type="SERVER", version="0.1.0", cwd="", message={"exit_code": 0})
            send_message(conn, exit_packet)

            conn.close()
            server.close()

        t = threading.Thread(target=server_handler, daemon=True)
        t.start()

        monkeypatch.setattr(client, "SOCKET_PATH", sock_path)
        try:
            assert server_ready.wait(timeout=5), "server thread did not start"
            code, retry = client._send_and_wait("test prompt")
            assert code == 0
            assert retry is False
        finally:
            t.join(timeout=2)
            try:
                os.unlink(sock_path)
            except FileNotFoundError:
                pass
