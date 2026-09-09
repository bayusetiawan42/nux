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
from nux.ui.spinner import SpinnerHandle

_TOOLS_SCHEMA = None
_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds per attempt multiplier


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
        reset_ts = self._parse_reset_ts(exc)
        save_rate_limit(key_id, reset_ts)

        if rotate_active():
            return

        wait_secs = max(0, reset_ts - int(time.time()))
        if wait_secs <= 0 or wait_secs > 120:
            raise AllKeysRateLimitedError(
                "All configured API keys are currently rate limited. Try again later."
            )

        time.sleep(wait_secs)
        if not rotate_active():
            raise AllKeysRateLimitedError(
                "All configured API keys are currently rate limited. Try again later."
            )

    @staticmethod
    def _error_code(exc: object) -> str:
        # Extract Groq's error code from an API error response body.
        try:
            body = exc.response.json()
        except (AttributeError, ValueError):
            return ""
        return body.get("error", {}).get("code", "")

    def _raise_for_api_error(self, exc: Exception) -> None:
        # Map provider errors to Nux errors. RateLimitError is handled by the
        # caller (key rotation); this method handles everything that cannot be
        # fixed by retrying. For unrecognized exceptions it returns without
        # raising, and the caller re-raises.
        exc_type = type(exc).__name__

        if exc_type == "AuthenticationError":
            raise AuthenticationFailedError(
                f"Authentication failed: {exc.message}"
            ) from exc

        if exc_type == "APIConnectionError":
            raise APIRequestError(f"Connection error: {exc}") from exc

        if exc_type in ("BadRequestError", "APIStatusError"):
            status = getattr(exc, "status_code", None)
            if self._error_code(exc) in ("tool_use_failed", "output_parse_failed"):
                raise APIRequestError(
                    "The model generated invalid output. "
                    "Try rephrasing your prompt with more detail."
                ) from exc
            message = getattr(exc, "message", str(exc))
            if status is not None:
                raise APIRequestError(f"API error ({status}): {message}") from exc
            raise APIRequestError(f"API error: {message}") from exc

    def _build_payload(self, messages: list[dict], tools: list[dict]) -> dict:
        payload: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_completion_tokens": self.config.max_completion_tokens,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        }
        if self.config.reasoning_effort is not None:
            payload["reasoning_effort"] = self.config.reasoning_effort
        if self.config.service_tier is not None:
            payload["service_tier"] = self.config.service_tier
        if self.config.user is not None:
            payload["user"] = self.config.user
        return payload

    def _try_chat(self, messages: list[dict], tools: list[dict]) -> ChatCompletion:
        all_keys = list_keys()
        attempts = max(len(all_keys), 1)

        for _ in range(attempts):
            key = active_key() or rotate_active()
            if key is None:
                raise AllKeysRateLimitedError(
                    "All configured API keys are currently rate limited. Try again later."
                )

            client = self._create_client(key)

            try:
                return client.chat.completions.create(**self._build_payload(messages, tools))
            except Exception as e:
                if type(e).__name__ == "RateLimitError":
                    self._handle_rate_limit(e, key.id)
                    continue
                self._raise_for_api_error(e)
                raise

        raise AllKeysRateLimitedError("All API keys exhausted or rate limited.")

    def chat(
        self,
        messages: list[dict],
        allowed_tools: list[str] | None = None,
        spinner: SpinnerHandle | None = None,
    ) -> ChatCompletion:
        tools = _tools_schema()
        if allowed_tools:
            normalized = {t.upper() for t in allowed_tools}
            tools = [
                t
                for t in tools
                if t.get("function", {}).get("name", "").upper() in normalized
            ]

        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self._try_chat(messages, tools)
            except (AllKeysRateLimitedError, AuthenticationFailedError, APIRequestError):
                raise
            except Exception as e:  # noqa: BLE001
                last_exc = e
                reason = type(e).__name__
                delay = _RETRY_DELAY * attempt
                if spinner:
                    spinner.push(f"#{attempt} {reason}. Retrying in {delay}s")
                time.sleep(delay)

        if last_exc:
            raise APIRequestError(
                f"Failed after {_MAX_RETRIES} retries: {last_exc}"
            ) from last_exc
        raise AllKeysRateLimitedError("All API keys exhausted or rate limited.")
