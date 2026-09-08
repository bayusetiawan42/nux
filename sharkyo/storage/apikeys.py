# storage/apikeys.py
# API key management with OS-keychain storage and round-robin rotation.

import json
import os
import time
from dataclasses import dataclass
from hashlib import sha256

from sharkyo.core.constants import SHARKYO_DIR
from sharkyo.storage.db import get_connection
from sharkyo.storage.schema import register_migration
from sharkyo.ui.display import print_info

_KEYRING_SERVICE = "sharkyo"


@dataclass
class ApiKey:
    id: int
    key: str
    base_url: str | None
    active: bool
    reset_at: int


def _secrets_file() -> str:
    return os.path.join(SHARKYO_DIR, "secrets.json")


def _secret_ref(key: str) -> str:
    return sha256(key.encode("utf-8")).hexdigest()


def _store_secret(key_ref: str, key: str) -> str:
    try:
        import keyring

        keyring.set_password(_KEYRING_SERVICE, key_ref, key)
        return "keyring"
    except Exception:  # noqa: BLE001 - keyring backends fail in many ways; fall back.
        print_info("OS keyring unavailable — storing API key in fallback file.")
        payload: dict[str, str] = {}
        if os.path.exists(_secrets_file()):
            try:
                with open(_secrets_file(), "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (OSError, ValueError):
                payload = {}
        payload[key_ref] = key
        fd = os.open(_secrets_file(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return "file"


def _load_secret_file(key_ref: str) -> str | None:
    if not os.path.exists(_secrets_file()):
        return None
    try:
        with open(_secrets_file(), "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get(key_ref)
    except (OSError, ValueError):
        return None


def _load_secret(key_ref: str, storage: str) -> str | None:
    if storage == "file":
        return _load_secret_file(key_ref)
    try:
        import keyring

        return keyring.get_password(_KEYRING_SERVICE, key_ref)
    except Exception:  # noqa: BLE001 - mirrors the tolerant fallback in _store_secret.
        return _load_secret_file(key_ref)


def _migrate_legacy(conn, schema_sql: str) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(apikeys)")}
    if "key_ref" in cols:
        return

    has_provider = "provider" in cols
    if has_provider:
        rows = conn.execute(
            "SELECT id, key, provider, base_url, active, reset_at FROM apikeys"
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, key, base_url, active, reset_at FROM apikeys").fetchall()
    conn.execute("ALTER TABLE apikeys RENAME TO apikeys_legacy")
    conn.executescript(schema_sql)
    for row in rows:
        if has_provider:
            _, plain_key, _provider, base_url, active, reset_at = row
        else:
            _, plain_key, base_url, active, reset_at = row
        key_ref = _secret_ref(plain_key)
        storage = _store_secret(key_ref, plain_key)
        conn.execute(
            """INSERT INTO apikeys (key_ref, base_url, active, reset_at, storage)
               VALUES (?, ?, ?, ?, ?)""",
            (key_ref, base_url, active, reset_at, storage),
        )
    conn.execute("DROP TABLE apikeys_legacy")


register_migration("apikeys", _migrate_legacy)


def has_keys() -> bool:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM apikeys").fetchone()[0]
    return count > 0


def list_keys() -> list[ApiKey]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, key_ref, base_url, active, reset_at, storage
               FROM apikeys ORDER BY id"""
        ).fetchall()

    keys = []
    for r in rows:
        keys.append(
            ApiKey(
                id=r["id"],
                key=_load_secret(r["key_ref"], r["storage"]) or "",
                base_url=r["base_url"],
                active=bool(r["active"]),
                reset_at=r["reset_at"],
            )
        )
    return keys


def active_key() -> ApiKey | None:
    now = int(time.time())
    with get_connection() as conn:
        row = conn.execute(
            """SELECT id, key_ref, base_url, active, reset_at, storage
               FROM apikeys WHERE active = 1 AND reset_at <= ? LIMIT 1""",
            (now,),
        ).fetchone()
    if not row:
        return None
    return ApiKey(
        id=row["id"],
        key=_load_secret(row["key_ref"], row["storage"]) or "",
        base_url=row["base_url"],
        active=bool(row["active"]),
        reset_at=row["reset_at"],
    )


def add_key(key: str, base_url: str | None = None) -> None:
    key = key.strip()
    key_ref = _secret_ref(key)
    storage = _store_secret(key_ref, key)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM apikeys").fetchone()[0]
        conn.execute(
            """INSERT OR IGNORE INTO apikeys (key_ref, base_url, active, storage)
               VALUES (?, ?, ?, ?)""",
            (
                key_ref,
                base_url.strip() if base_url else None,
                1 if count == 0 else 0,
                storage,
            ),
        )
        conn.commit()


def set_active(key_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE apikeys SET active = 0")
        conn.execute("UPDATE apikeys SET active = 1 WHERE id = ?", (key_id,))
        conn.commit()


def rotate_active() -> ApiKey | None:
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
    with get_connection() as conn:
        conn.execute("UPDATE apikeys SET reset_at = ? WHERE id = ?", (reset_ts, key_id))
        conn.commit()
