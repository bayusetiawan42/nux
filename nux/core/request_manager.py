# core/request_manager.py
# Sends chat completions using the Groq SDK with automatic key rotation on rate limits.

from __future__ import annotations

import time

from nux.core.config import Config, get_config
from nux.core.errors import (
    AllKeysRateLimitedError,
    APIRequestError,
    AuthenticationFailedError,
    NoAPIKeyError,
)
from nux.core.llm import ChatCompletion, Groq
from nux.storage.apikeys import (
    ApiKey,
    active_key,
    has_keys,
    list_keys,
    rotate_active,
    save_rate_limit,
)
from nux.ui.display import print_info

_TOOLS_SCHEMA = None


def _tools_schema() -> list:
    global _TOOLS_SCHEMA
    if _TOOLS_SCHEMA is None:
        from nux.tools import TOOLS_SCHEMA as schema

        _TOOLS_SCHEMA = schema
    return _TOOLS_SCHEMA


class RequestManager:
    def __init__(self, config: Config | None = None) -> None:
        self.config = get_config(config)
        if not has_keys():
            raise NoAPIKeyError("No active API key. Add one with: nux --add-key KEY")

    def _create_client(self, key: ApiKey) -> Groq:
        return Groq()(api_key=key.key, base_url=key.base_url)

    @staticmethod
    def _parse_reset_ts(exc: object) -> int:
        now = int(time.time())
        reset_ts = now + 60
        try:
            headers = exc.response.headers
            for header_name in (
                "retry-after",
                "x-ratelimit-reset-requests",
                "x-ratelimit-reset-tokens",
            ):
                val = headers.get(header_name)
                if not val:
                    continue
                seconds = float(val)
                reset_ts = int(now + seconds) if seconds < now else int(seconds)
                break
        except (AttributeError, TypeError, ValueError):
            pass
        return reset_ts

    def _handle_rate_limit(self, exc: object, key_id: int) -> None:
        save_rate_limit(key_id, self._parse_reset_ts(exc))
        new_key = rotate_active()
        if new_key:
            print_info("Rate limit hit. Rotated to next API key.")
        else:
            raise AllKeysRateLimitedError(
                "All configured API keys are currently rate limited. Try again later."
            )

    def chat(self, messages: list[dict]) -> ChatCompletion:
        all_keys = list_keys()
        attempts = max(len(all_keys), 1)

        for _ in range(attempts):
            key = active_key()
            if key is None:
                key = rotate_active()
            if key is None:
                raise AllKeysRateLimitedError(
                    "All configured API keys are currently rate limited. Try again later."
                )

            try:
                client = self._create_client(key)

                payload: dict = {
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_completion_tokens": self.config.max_completion_tokens,
                    "tools": _tools_schema(),
                    "tool_choice": "auto",
                    "parallel_tool_calls": True,
                }

                if self.config.reasoning_effort is not None:
                    payload["reasoning_effort"] = self.config.reasoning_effort
                if self.config.service_tier is not None:
                    payload["service_tier"] = self.config.service_tier
                if self.config.user is not None:
                    payload["user"] = self.config.user

                return client.chat.completions.create(**payload)
            except Exception as e:
                exc_type = type(e).__name__
                if exc_type == "RateLimitError":
                    self._handle_rate_limit(e, key.id)
                    continue
                if exc_type == "AuthenticationError":
                    raise AuthenticationFailedError(f"Authentication failed: {e.message}") from e
                if exc_type == "APIConnectionError":
                    raise APIRequestError(f"Connection error: {e}") from e
                if exc_type == "APIStatusError":
                    raise APIRequestError(f"API error ({e.status_code}): {e.message}") from e
                raise

        raise AllKeysRateLimitedError("All API keys exhausted or rate limited.")
