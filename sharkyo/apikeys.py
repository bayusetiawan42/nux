# apikeys.py
# API key management with multi-provider and round-robin rotation.

import time
from dataclasses import dataclass

from sharkyo.db import get_connection


@dataclass
class ApiKey:
    id: int
    key: str
    provider: str
    base_url: str | None
    active: bool
    reset_at: int


def list_keys() -> list[ApiKey]:
    # Return all configured API keys.
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, key, provider, base_url, active, reset_at FROM apikeys ORDER BY id"
        ).fetchall()
    return [
        ApiKey(
            id=r["id"],
            key=r["key"],
            provider=r["provider"],
            base_url=r["base_url"],
            active=bool(r["active"]),
            reset_at=r["reset_at"],
        )
        for r in rows
    ]


def active_key() -> ApiKey | None:
    # Return the currently active API key, or None.
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, key, provider, base_url FROM apikeys WHERE active = 1 LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return ApiKey(
        id=row["id"],
        key=row["key"],
        provider=row["provider"],
        base_url=row["base_url"],
        active=True,
        reset_at=0,
    )


def add_key(key: str, provider: str = "groq", base_url: str | None = None) -> None:
    # Add a new API key. Sets it active if it is the first key added.
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM apikeys").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO apikeys (key, provider, base_url, active) VALUES (?, ?, ?, ?)",
            (
                key.strip(),
                provider.strip(),
                base_url.strip() if base_url else None,
                1 if count == 0 else 0,
            ),
        )
        conn.commit()


def set_active(key_id: int) -> None:
    # Mark a specific key as active, deactivating all others.
    with get_connection() as conn:
        conn.execute("UPDATE apikeys SET active = 0")
        conn.execute("UPDATE apikeys SET active = 1 WHERE id = ?", (key_id,))
        conn.commit()


def rotate_active() -> ApiKey | None:
    # Rotate round-robin to the next non-rate-limited key.
    now = int(time.time())
    keys = list_keys()
    if not keys:
        return None

    current_id = next((k.id for k in keys if k.active), keys[0].id)
    n = len(keys)
    start = next((i for i, k in enumerate(keys) if k.id == current_id), 0)

    for offset in range(1, n + 1):
        candidate = keys[(start + offset) % n]
        if candidate.reset_at <= now:
            set_active(candidate.id)
            return candidate
    return None


def save_rate_limit(key_id: int, reset_ts: int) -> None:
    # Record rate-limit reset timestamp for a key.
    with get_connection() as conn:
        conn.execute("UPDATE apikeys SET reset_at = ? WHERE id = ?", (reset_ts, key_id))
        conn.commit()
