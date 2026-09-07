# sharkyo/llm.py
# Backward-compat re-export. Import from sharkyo.core.llm instead.
from sharkyo.core.llm import ChatCompletion, ChatCompletionMessageToolCall, OpenAI, errors

__all__ = ["ChatCompletion", "ChatCompletionMessageToolCall", "OpenAI", "errors"]
