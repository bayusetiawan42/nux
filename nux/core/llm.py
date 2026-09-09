# core/llm.py
# Lazy accessors for the Groq SDK.

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from groq import Groq
    from groq.types.chat import ChatCompletion, ChatCompletionMessageToolCall

_GROQ = None


def _get_groq() -> Any:
    global _GROQ
    if _GROQ is None:
        _GROQ = importlib.import_module("groq")
    return _GROQ


def Groq() -> Any:
    return _get_groq().Groq


def ChatCompletion() -> Any:
    return _get_groq().types.chat.ChatCompletion


def ChatCompletionMessageToolCall() -> Any:
    return _get_groq().types.chat.ChatCompletionMessageToolCall


def errors() -> Any:
    return _get_groq()
