# tests/test_request_manager.py
# RequestManager error handling and rate-limit parsing tests.

import time

import pytest

from sharkyo.config import Config
from sharkyo.request_manager import NoAPIKeyError, RequestManager


def _fake_exc(headers: dict) -> object:
    # Build a minimal stand-in for RateLimitError.v
    resp = type("Response", (), {"headers": headers})()
    return type("Exc", (), {"response": resp})()


def test_no_keys_raises():
    with pytest.raises(NoAPIKeyError):
        RequestManager(Config())


def test_parse_reset_ts_relative_and_absolute():
    now = int(time.time())

    relative = RequestManager._parse_reset_ts(_fake_exc({"retry-after": "30"}))
    assert relative == now + 30

    future = now + 500
    absolute = RequestManager._parse_reset_ts(_fake_exc({"x-ratelimit-reset-requests": str(future)}))
    assert absolute == future

    fallback = RequestManager._parse_reset_ts(_fake_exc({}))
    assert now + 60 <= fallback <= now + 61