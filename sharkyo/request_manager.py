"""Sends chat completions using openai SDK (works for Groq + OpenAI)."""

import sys
import time

from openai import OpenAI, RateLimitError, APIStatusError

from sharkyo.apikeys import active_key, rotate_active, save_rate_limit, list_keys
from sharkyo.display import print_error, print_info
from sharkyo.rcfiles import load_rc, rc_float, rc_int, rc_str
from sharkyo.tools_schema import TOOLS_SCHEMA

_GROQ_BASE = "https://api.groq.com/openai/v1"


class RequestManager:
    def __init__(self) -> None:
        if not active_key():
            print_error("No active API key. Add one with: sharkyo --add-key KEY")
            sys.exit(1)

    def _client(self, key_info: dict) -> OpenAI:
        base_url = key_info["base_url"]
        if base_url is None and key_info["provider"] == "groq":
            base_url = _GROQ_BASE
        return OpenAI(api_key=key_info["key"], base_url=base_url)

    def _rotate(self, e: RateLimitError, key_id: int) -> None:
        """Parse rate-limit headers and rotate to next available key."""
        reset_ts = int(time.time()) + 60  # default: 60s from now
        try:
            headers = e.response.headers
            for h in ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
                val = headers.get(h)
                if val:
                    v = int(float(val))
                    reset_ts = v if v > int(time.time()) else int(time.time()) + v
                    break
        except Exception:
            pass
        save_rate_limit(key_id, reset_ts)
        new_key = rotate_active()
        if new_key:
            print_info("Rotated to another API key.")
        else:
            print_error("All API keys are rate limited. Try again later.")
            sys.exit(1)

    def chat(self, messages: list) -> object:
        rc = load_rc()
        n_keys = max(len(list_keys()), 1)

        for _ in range(n_keys):
            key_info = active_key()
            if not key_info:
                print_error("No active API key.")
                sys.exit(1)
            try:
                client = self._client(key_info)
                return client.chat.completions.create(
                    model=rc_str(rc, "model"),
                    messages=messages,
                    temperature=rc_float(rc, "temperature"),
                    max_completion_tokens=rc_int(rc, "max_tokens"),
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                )
            except RateLimitError as e:
                self._rotate(e, key_info["id"])
            except APIStatusError as e:
                print_error(f"API error: {e.message}")
                sys.exit(1)

        print_error("All API keys are rate limited.")
        sys.exit(1)
