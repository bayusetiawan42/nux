# llm.py
# Lazy accessors for the OpenAI SDK.
#
# `import openai` is the single most expensive step of Sharkyo startup
# (~1.1s): it pulls in pydantic, httpx, and the whole typed API surface. The
# background daemon absorbs that cost once, but the CLI must also stay fast
# on the fallback (in-process) path — so these accessors defer the import
# until the SDK is actually needed at request time.

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type-checking only; never imported at runtime.
    from openai import OpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall

_OPENAI = None


def _get_openai() -> Any:
    # Import (once) and cache the openai module on first use.
    global _OPENAI
    if _OPENAI is None:
        _OPENAI = importlib.import_module("openai")
    return _OPENAI


def OpenAI() -> Any:
    # Return the OpenAI client class, importing lazily on first use.
    return _get_openai().OpenAI


def ChatCompletion() -> Any:
    # Return the ChatCompletion type, importing lazily on first use.
    return _get_openai().types.chat.ChatCompletion


def ChatCompletionMessageToolCall() -> Any:
    # Return the ChatCompletionMessageToolCall type, importing lazily.
    return _get_openai().types.chat.ChatCompletionMessageToolCall


def errors() -> Any:
    # Return the openai.errors module (APIConnectionError, APIStatusError,
    # AuthenticationError, RateLimitError, ...).
    return _get_openai()
