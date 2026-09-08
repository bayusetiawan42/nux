# tests/conftest.py
# Shared fixtures: isolated DB location and in-memory fake OS keychain.

import keyring
import pytest


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    # Point the app DB (and the keyring fallback dir) at a temp location per test.
    monkeypatch.setattr("sharkyo.storage.db.DB_FILE", str(tmp_path / "data.db"))
    monkeypatch.setattr("sharkyo.core.constants.SHARKYO_DIR", str(tmp_path))

    # Reset the schema initialization tracker so each test gets a fresh DB.
    import sharkyo.storage.db
    monkeypatch.setattr(sharkyo.storage.db, "_initialized_file", None)


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    # Replace the OS keychain with an in-memory fake for deterministic tests.
    store = {}

    def set_password(service, username, password):
        store[(service, username)] = password

    def get_password(service, username):
        return store.get((service, username))

    monkeypatch.setattr(keyring, "set_password", set_password)
    monkeypatch.setattr(keyring, "get_password", get_password)
    return store
