# core/llm.py
# Lazy accessors for the OpenAI SDK.

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import OpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall

_OPENAI = None


def _get_openai() -> Any:
    global _OPENAI
    if _OPENAI is None:
        _OPENAI = importlib.import_module("openai")
    return _OPENAI


def OpenAI() -> Any:
    return _get_openai().OpenAI


def ChatCompletion() -> Any:
    return _get_openai().types.chat.ChatCompletion


def ChatCompletionMessageToolCall() -> Any:
    return _get_openai().types.chat.ChatCompletionMessageToolCall


def errors() -> Any:
    return _get_openai()
