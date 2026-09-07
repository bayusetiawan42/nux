# request_manager.py
# Sends chat completions using the OpenAI SDK with automatic key rotation on rate limits.

import sys
import time

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletion

from sharkyo.apikeys import ApiKey, active_key, list_keys, rotate_active, save_rate_limit
from sharkyo.config import Config, load_config
from sharkyo.display import print_error, print_info
from sharkyo.tools import TOOLS_SCHEMA

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class RequestManager:
    # Manages LLM API requests and transparent key rotation on rate limit errors.

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        if not active_key():
            print_error("No active API key. Add one with: sharkyo --add-key KEY")
            sys.exit(1)

    def _create_client(self, key: ApiKey) -> OpenAI:
        # Build an OpenAI client for the given key, inferring base URL from provider.
        base_url = key.base_url
        if base_url is None and key.provider == "groq":
            base_url = _GROQ_BASE_URL
        return OpenAI(api_key=key.key, base_url=base_url)

    def _handle_rate_limit(self, exc: RateLimitError, key_id: int) -> None:
        # Parse rate-limit headers and mark the key as rate-limited.
        # Rotate to the next available key, or exit if all are exhausted.
        reset_ts = int(time.time()) + 60  # Default fallback: 60 seconds.
        try:
            headers = exc.response.headers
            for header_name in (
                "retry-after",
                "x-ratelimit-reset-requests",
                "x-ratelimit-reset-tokens",
            ):
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

    def chat(self, messages: list[dict]) -> ChatCompletion:
        # Execute a chat completion with automatic retry across available keys.
        # Tries each key at most once before giving up.
        all_keys = list_keys()
        attempts = max(len(all_keys), 1)

        for _ in range(attempts):
            key = active_key()
            if not key:
                print_error("No active API key found.")
                sys.exit(1)

            try:
                client = self._create_client(key)
                return client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_completion_tokens=self.config.max_tokens,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                )
            except RateLimitError as e:
                self._handle_rate_limit(e, key.id)
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
