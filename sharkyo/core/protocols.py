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
    model: str
    max_history: int
    cmd_out_chars: int
    cmd_timeout: float
    temperature: float
    max_tokens: int
