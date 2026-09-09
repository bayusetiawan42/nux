# tests/test_protocol.py
# Wire protocol tests: Packet serialization, send/recv, edge cases.

import socket
import threading

import pytest

from nux.server.protocol import Packet, recv_message, send_message


class TestPacket:
    def test_to_dict(self):
        packet = Packet(type="CLIENT", version="0.1.0", cwd="/tmp", message={"prompt": "hello"})
        d = packet.to_dict()
        assert d["type"] == "CLIENT"
        assert d["version"] == "0.1.0"
        assert d["cwd"] == "/tmp"
        assert d["message"] == {"prompt": "hello"}

    def test_from_dict(self):
        data = {"type": "SERVER", "version": "0.2.0", "cwd": "/home", "message": {"pid": 1234}}
        packet = Packet.from_dict(data)
        assert packet.type == "SERVER"
        assert packet.version == "0.2.0"
        assert packet.cwd == "/home"
        assert packet.message == {"pid": 1234}

    def test_from_dict_defaults(self):
        data = {"type": "CLIENT"}
        packet = Packet.from_dict(data)
        assert packet.version == ""
        assert packet.cwd == ""
        assert packet.message == {}

    def test_roundtrip(self):
        original = Packet(type="CLIENT", version="1.0", cwd="/test", message={"prompt": "hi"})
        d = original.to_dict()
        restored = Packet.from_dict(d)
        assert restored == original


class TestSendRecv:
    # Create a connected socket pair for testing.
    def _make_pair(self):
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind("/tmp/test_nux_proto.sock")
        server_sock.listen(1)

        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_sock.connect("/tmp/test_nux_proto.sock")
        conn, _ = server_sock.accept()

        return client_sock, conn

    def teardown_method(self):
        import os

        try:
            os.unlink("/tmp/test_nux_proto.sock")
        except FileNotFoundError:
            pass

    def test_send_recv_server_packet(self):
        client, server = self._make_pair()
        try:
            packet = Packet(type="SERVER", version="0.1.0", cwd="", message={"exit_code": 0})
            send_message(server, packet)

            received, fds = recv_message(client)
            assert received.type == "SERVER"
            assert received.message == {"exit_code": 0}
            assert fds == []
        finally:
            client.close()
            server.close()

    def test_send_recv_client_packet_no_fds(self):
        # Client packet without FDs should still work.
        client, server = self._make_pair()
        try:
            packet = Packet(type="CLIENT", version="0.1.0", cwd="/tmp", message={"prompt": "test"})
            send_message(server, packet)

            received, fds = recv_message(client)
            assert received.type == "CLIENT"
            assert received.message == {"prompt": "test"}
        finally:
            client.close()
            server.close()

    def test_large_message(self):
        client, server = self._make_pair()
        try:
            large_msg = "x" * 100000
            packet = Packet(type="SERVER", version="0.1.0", cwd="", message={"data": large_msg})
            send_message(server, packet)

            received, _ = recv_message(client)
            assert received.message["data"] == large_msg
        finally:
            client.close()
            server.close()

    def test_unicode_message(self):
        client, server = self._make_pair()
        try:
            packet = Packet(type="SERVER", version="0.1.0", cwd="", message={"text": "你好世界"})
            send_message(server, packet)

            received, _ = recv_message(client)
            assert received.message["text"] == "你好世界"
        finally:
            client.close()
            server.close()

    def test_empty_message(self):
        client, server = self._make_pair()
        try:
            packet = Packet(type="SERVER", version="0.1.0", cwd="")
            send_message(server, packet)

            received, _ = recv_message(client)
            assert received.message == {}
        finally:
            client.close()
            server.close()
