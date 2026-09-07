# request_manager.py
# Sends chat completions using the OpenAI SDK with automatic key rotation on rate limits.

from __future__ import annotations

import time

from sharkyo.apikeys import ApiKey, active_key, has_keys, list_keys, rotate_active, save_rate_limit
from sharkyo.display import print_info
from sharkyo.llm import ChatCompletion, OpenAI

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_TOOLS_SCHEMA = None


def _tools_schema() -> list:
    # Lazy: pull the tool registry only when a request actually goes out.
    # Resolving this at import time drags in the full tool stack (questionary,
    # pty, etc.) on every fast CLI path.
    global _TOOLS_SCHEMA
    if _TOOLS_SCHEMA is None:
        from sharkyo.tools import TOOLS_SCHEMA as schema

        _TOOLS_SCHEMA = schema
    return _TOOLS_SCHEMA


class SharkyoError(Exception):
    # Base error for all Sharkyo request failures.
    pass


class NoAPIKeyError(SharkyoError):
    pass


class AllKeysRateLimitedError(SharkyoError):
    pass


class AuthenticationFailedError(SharkyoError):
    pass


class APIRequestError(SharkyoError):
    pass


class RequestManager:
    # Manages LLM API requests and transparent key rotation on rate limit errors.

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        if not has_keys():
            raise NoAPIKeyError("No active API key. Add one with: sharkyo --add-key KEY")

    def _create_client(self, key: ApiKey) -> OpenAI:
        # Build an OpenAI client for the given key, inferring base URL from provider.
        # OpenAI() lazily resolves the SDK class; call it to instantiate.
        base_url = key.base_url
        if base_url is None and key.provider == "groq":
            base_url = _GROQ_BASE_URL
        return OpenAI()(api_key=key.key, base_url=base_url)

    @staticmethod
    def _parse_reset_ts(exc: "object") -> int:
        # Parse the rate-limit reset time from response headers, defaulting to 60s.
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
                # retry-after is a relative duration; x-ratelimit-reset-* are absolute epochs.
                # The heuristic: values smaller than the current epoch are relative seconds.
                reset_ts = int(now + seconds) if seconds < now else int(seconds)
                break
        except (AttributeError, TypeError, ValueError):
            pass
        return reset_ts

    def _handle_rate_limit(self, exc: "object", key_id: int) -> None:
        # Record the rate limit, then rotate to the next available key.
        save_rate_limit(key_id, self._parse_reset_ts(exc))
        new_key = rotate_active()
        if new_key:
            print_info("Rate limit hit. Rotated to next API key.")
        else:
            raise AllKeysRateLimitedError(
                "All configured API keys are currently rate limited. Try again later."
            )

    def chat(self, messages: list[dict]) -> ChatCompletion:
        # Execute a chat completion with automatic retry across available keys.
        # Tries each key at most once before giving up.
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
                return client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_completion_tokens=self.config.max_tokens,
                    tools=_tools_schema(),
                    tool_choice="auto",
                )
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