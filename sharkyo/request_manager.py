"""Sends chat completions using OpenAI SDK with automatic key rotation on rate limits."""

import sys
import time
from typing import Any

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError

from sharkyo.apikeys import active_key, list_keys, rotate_active, save_rate_limit
from sharkyo.config import Config, load_config
from sharkyo.display import print_error, print_info
from sharkyo.tools import TOOLS_SCHEMA

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class RequestManager:
    """Manages LLM API requests and key rotation."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        if not active_key():
            print_error("No active API key. Add one with: sharkyo --add-key KEY")
            sys.exit(1)

    def _create_client(self, key_info: dict) -> OpenAI:
        base_url = key_info["base_url"]
        if base_url is None and key_info["provider"] == "groq":
            base_url = _GROQ_BASE_URL
        return OpenAI(api_key=key_info["key"], base_url=base_url)

    def _handle_rate_limit(self, exc: RateLimitError, key_id: int) -> None:
        """Parse rate-limit headers and rotate to the next available API key."""
        reset_ts = int(time.time()) + 60  # default fallback: 60s
        try:
            headers = exc.response.headers
            for header_name in ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
                val = headers.get(header_name)
                if val:
                    num = int(float(val))
                    reset_ts = num if num > int(time.time()) else int(time.time()) + num
                    break
        except Exception:
            pass

        save_rate_limit(key_id, reset_ts)
        new_key = rotate_active()
        if new_key:
            print_info("Rate limit hit. Rotated to next API key.")
        else:
            print_error("All configured API keys are currently rate limited. Try again later.")
            sys.exit(1)

    def chat(self, messages: list[dict[str, Any]]) -> Any:
        """Execute chat completion with automatic retry/rotation across available keys."""
        all_keys = list_keys()
        attempts = max(len(all_keys), 1)

        for _ in range(attempts):
            key_info = active_key()
            if not key_info:
                print_error("No active API key found.")
                sys.exit(1)

            try:
                client = self._create_client(key_info)
                return client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_completion_tokens=self.config.max_tokens,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                )
            except RateLimitError as e:
                self._handle_rate_limit(e, key_info["id"])
            except AuthenticationError as e:
                print_error(f"Authentication failed: {e.message}")
                sys.exit(1)
            except APIConnectionError as e:
                print_error(f"Connection error: {e}")
                sys.exit(1)
            except APIStatusError as e:
                print_error(f"API error ({e.status_code}): {e.message}")
                sys.exit(1)

        print_error("All API keys exhausted or rate limited.")
        sys.exit(1)
