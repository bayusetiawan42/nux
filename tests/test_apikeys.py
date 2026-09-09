# tests/test_apikeys.py
# API key storage, rotation, and legacy migration tests.

import sqlite3
import time

import nux.storage.db
from nux.storage import apikeys


def test_add_and_list(fake_keyring):
    apikeys.add_key("secret-1")
    apikeys.add_key("secret-2", base_url="https://x")

    keys = apikeys.list_keys()
    assert len(keys) == 2
    assert [k.key for k in keys] == ["secret-1", "secret-2"]
    assert apikeys.active_key().key == "secret-1"

    # Raw secrets must never live in the database, only a keyring reference.
    rows = (
        sqlite3.connect(nux.storage.db.DB_FILE)
        .execute("SELECT key_ref, storage FROM apikeys ORDER BY id")
        .fetchall()
    )
    assert all(k not in ("secret-1", "secret-2") for k, _ in rows)
    assert all(storage == "keyring" for _, storage in rows)


def test_duplicate_key_is_ignored(fake_keyring):
    apikeys.add_key("dup")
    apikeys.add_key("dup")
    assert len(apikeys.list_keys()) == 1


def test_active_key_skips_rate_limited(fake_keyring):
    apikeys.add_key("a")
    apikeys.add_key("b")

    rotated = apikeys.rotate_active()
    assert rotated.key == "b"
    apikeys.save_rate_limit(rotated.id, int(time.time()) + 60)

    # The active key is now rate-limited, so active_key() must not return it,
    # and rotation must fall back to the other key.
    assert apikeys.active_key() is None
    assert apikeys.rotate_active().key == "a"
    assert apikeys.active_key().key == "a"

    # Rate-limit the remaining key -> no rotation possible.
    apikeys.save_rate_limit(apikeys.active_key().id, int(time.time()) + 60)
    assert apikeys.rotate_active() is None


def test_migrates_legacy_plaintext_schema(fake_keyring, tmp_path):
    # Simulate a DB created by the pre-keyring schema (plaintext 'key' column).
    conn = sqlite3.connect(str(tmp_path / "data.db"))
    conn.execute(
        """CREATE TABLE apikeys (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            key      TEXT NOT NULL UNIQUE,
            base_url TEXT,
            active   INTEGER NOT NULL DEFAULT 0,
            reset_at INTEGER NOT NULL DEFAULT 0
        )"""
    )
    conn.execute("INSERT INTO apikeys (key, active) VALUES ('legacy-secret', 1)")
    conn.commit()
    conn.close()

    keys = apikeys.list_keys()
    assert len(keys) == 1
    assert keys[0].key == "legacy-secret"
    assert apikeys.active_key().key == "legacy-secret"

    # After migration the table no longer holds the plaintext.
    cols = {
        r[1]
        for r in sqlite3.connect(str(tmp_path / "data.db")).execute("PRAGMA table_info(apikeys)")
    }
    assert "key_ref" in cols and "key" not in cols
