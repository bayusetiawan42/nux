"""API key management with multi-provider and round-robin rotation."""

import sqlite3
import time

from sharkyo.constants import DB_FILE


def _conn() -> sqlite3.Connection:
    db = sqlite3.connect(DB_FILE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS apikeys (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            key      TEXT    NOT NULL UNIQUE,
            provider TEXT    NOT NULL DEFAULT 'groq',
            base_url TEXT,
            active   INTEGER NOT NULL DEFAULT 0,
            reset_at INTEGER NOT NULL DEFAULT 0
        )
    """)
    db.commit()
    return db


def list_keys() -> list[dict]:
    with _conn() as db:
        rows = db.execute(
            "SELECT id, key, provider, base_url, active, reset_at FROM apikeys ORDER BY id"
        ).fetchall()
    return [
        {"id": r[0], "key": r[1], "provider": r[2], "base_url": r[3],
         "active": bool(r[4]), "reset_at": r[5]}
        for r in rows
    ]


def active_key() -> dict | None:
    with _conn() as db:
        row = db.execute(
            "SELECT id, key, provider, base_url FROM apikeys WHERE active = 1 LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return {"id": row[0], "key": row[1], "provider": row[2], "base_url": row[3]}


def add_key(key: str, provider: str = "groq", base_url: str | None = None) -> None:
    with _conn() as db:
        count = db.execute("SELECT COUNT(*) FROM apikeys").fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO apikeys (key, provider, base_url, active) VALUES (?, ?, ?, ?)",
            (key, provider, base_url, 1 if count == 0 else 0),
        )
        db.commit()


def _set_active(key_id: int) -> None:
    with _conn() as db:
        db.execute("UPDATE apikeys SET active = 0")
        db.execute("UPDATE apikeys SET active = 1 WHERE id = ?", (key_id,))
        db.commit()


def rotate_active() -> dict | None:
    now = int(time.time())
    keys = list_keys()
    if not keys:
        return None
    current_id = next((k["id"] for k in keys if k["active"]), keys[0]["id"])
    n = len(keys)
    start = next((i for i, k in enumerate(keys) if k["id"] == current_id), 0)
    for offset in range(1, n + 1):
        candidate = keys[(start + offset) % n]
        if candidate["reset_at"] <= now:
            _set_active(candidate["id"])
            return candidate
    return None


def save_rate_limit(key_id: int, reset_ts: int) -> None:
    with _conn() as db:
        db.execute("UPDATE apikeys SET reset_at = ? WHERE id = ?", (reset_ts, key_id))
        db.commit()
