# server/protocol.py
# Universal socket wire protocol — Packet-based send/recv with SCM_RIGHTS FD passing.

from __future__ import annotations

import array
import json
import socket
import struct
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Packet:
    type: str  # "CLIENT" | "SERVER"
    version: str
    cwd: str
    env: dict[str, str]

    # Standard message dict:
    # "prompt": str   -> prompt to model  (server/daemon)

    message: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "version": self.version,
            "cwd": self.cwd,
            "env": self.env,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Packet:
        return cls(
            type=data["type"],
            version=data.get("version", ""),
            cwd=data.get("cwd", ""),
            env=data.get("env", {}),
            message=data.get("message", {}),
        )


# Internal helpers (private)


def _recv_exactly(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise OSError("client closed connection while sending data")
        buf.extend(chunk)
    return bytes(buf)


def _recv_fds(conn: socket.socket, count: int = 3) -> list[int]:
    fds: list[int] = []
    spins = 0
    while len(fds) < count:
        _, ancdata, _, _ = conn.recvmsg(1, socket.CMSG_SPACE(max(count * 4, 4)))
        if not ancdata:
            spins += 1
            if spins > 100:
                raise OSError("no SCM_RIGHTS descriptors received")
            continue
        spins = 0
        for level, ctype, cdata in ancdata:
            if level == socket.SOL_SOCKET and ctype == socket.SCM_RIGHTS:
                fds.extend(int(fd) for fd in array.array("i", cdata[: count * 4]))
    return fds[:count]


def _send_fds(conn: socket.socket) -> None:
    fds = array.array("i", [0, 1, 2]).tobytes()
    conn.sendmsg(
        [b" "],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)],
    )


def _recv_int(conn: socket.socket) -> int | None:
    buf = b""
    while len(buf) < 4:
        try:
            chunk = conn.recv(4 - len(buf))
        except InterruptedError:
            continue
        if not chunk:
            return None
        buf += chunk
    return struct.unpack("!i", buf)[0]


# Public API


def send_message(conn: socket.socket, packet: Packet) -> None:
    data = json.dumps(packet.to_dict(), ensure_ascii=False).encode("utf-8")
    conn.sendall(struct.pack("!I", len(data)) + data)
    if packet.type == "CLIENT":
        _send_fds(conn)


def recv_message(conn: socket.socket) -> tuple[Packet, list[int]]:
    (length,) = struct.unpack("!I", _recv_exactly(conn, 4))
    raw = _recv_exactly(conn, length).decode("utf-8")
    packet = Packet.from_dict(json.loads(raw))
    fds: list[int] = []
    if packet.type == "CLIENT":
        fds = _recv_fds(conn)
    return packet, fds
