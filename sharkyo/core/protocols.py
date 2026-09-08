# core/protocols.py
# Interface definitions for pluggable components.

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    def execute(self, sql: str, params: tuple = ()) -> object: ...
    def commit(self) -> None: ...


@runtime_checkable
class SearchEngine(Protocol):
    def search(self, query: str, top_k: int = 3) -> list: ...


@runtime_checkable
class ToolHandler(Protocol):
    def __call__(self, args: dict, config: object) -> object: ...


@runtime_checkable
class ConfigProvider(Protocol):
    model: str = "openai/gpt-oss-20b"
    max_history: int = 12
    max_command_output_display: int = 2000  # Chars
    max_command_output_tokens: int = 1200  # Tokens
    max_completion_tokens: int = 512
    temperature: float = 0.7
    reasoning_effort: str | None = None
    service_tier: str | None = None
    user: str | None = None
