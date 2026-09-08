# server/protocol.py
# Socket wire protocol helpers for SCM_RIGHTS FD passing.

from __future__ import annotations

import array
import json
import socket
import struct


def recv_exactly(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise OSError("client closed connection while sending data")
        buf.extend(chunk)
    return bytes(buf)


def recv_dict(conn: socket.socket) -> dict:
    (length,) = struct.unpack("!I", recv_exactly(conn, 4))
    raw = recv_exactly(conn, length).decode("utf-8")
    return json.loads(raw)


def recv_fds(conn: socket.socket, count: int = 3) -> list[int]:
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


def send_fds(conn: socket.socket) -> None:
    fds = array.array("i", [0, 1, 2]).tobytes()
    conn.sendmsg(
        [b" "],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)],
    )


def send_dict(conn: socket.socket, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    conn.sendall(struct.pack("!I", len(data)) + data)


def recv_int(conn: socket.socket) -> int | None:
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
