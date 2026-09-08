# core/agent.py
# Agentic loop and conversation manager for Sharkyo.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sharkyo.core.config import Config, get_config
from sharkyo.core.constants import SYSTEM_PROMPT
from sharkyo.core.context import get_environment_context
from sharkyo.core.request_manager import RequestManager
from sharkyo.search import BM25Searcher
from sharkyo.storage.history import HistoryManager
from sharkyo.storage.knowledge import KnowledgeManager
from sharkyo.tools import dispatch_tool
from sharkyo.tools.result import ToolResult, serialize_tool_call
from sharkyo.ui.display import print_error, print_reply, yaspin_if_tty

if TYPE_CHECKING:
    from groq.types.chat import ChatCompletionMessageToolCall

MAX_TOOL_ITERATIONS = 10


class Agent:
    def __init__(self, config: Config | None = None) -> None:
        self.config = get_config(config)
        self.history_mgr = HistoryManager(self.config.max_history)
        self.knowledge_mgr = KnowledgeManager()
        self.request_mgr = RequestManager(self.config)
        self._searcher = BM25Searcher()

    # ---- Prompt construction ----

    def _build_system_prompt(self) -> str:
        prompt = SYSTEM_PROMPT

        entries = self.knowledge_mgr.list_all()
        if entries:
            block = "\n".join(f"{k} = {v}" for k, v in entries)
            prompt += f"\n\n<user_knowledge>\n{block}\n</user_knowledge>"

        prompt += f"\n\n<environment_context>\n{get_environment_context()}\n</environment_context>"
        return prompt

    def _build_skill_hint(self, user_input: str) -> str | None:
        results = self._searcher.search(user_input, top_k=3)
        if not results:
            return None
        names = ", ".join(f"'{r.name}'" for r in results)
        return (
            f"[Relevant skills: {names}. Consider calling SKILL with one of these before acting.]"
        )

    def _build_messages(self, user_input: str, history: list[dict]) -> list[dict]:
        skill_hint = self._build_skill_hint(user_input)
        augmented_input = f"{skill_hint}\n\n{user_input}" if skill_hint else user_input
        return (
            [{"role": "system", "content": self._build_system_prompt()}]
            + history
            + [{"role": "user", "content": augmented_input}]
        )

    # ---- Tool helpers ----

    def _parse_tool_args(self, tc: ChatCompletionMessageToolCall) -> dict:
        try:
            return json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            return {}

    def _execute_tools(
        self,
        tool_calls: list[ChatCompletionMessageToolCall],
    ) -> tuple[list[tuple[ChatCompletionMessageToolCall, ToolResult]], bool]:
        executed: list[tuple[ChatCompletionMessageToolCall, ToolResult]] = []
        for tc in tool_calls:
            result = dispatch_tool(tc.function.name, self._parse_tool_args(tc), self.config)
            executed.append((tc, result))
            if not result.should_continue:
                return executed, True
        return executed, False

    def _record_tool_results(
        self,
        messages: list[dict],
        executed: list[tuple[ChatCompletionMessageToolCall, ToolResult]],
        text_reply: str,
    ) -> None:
        self.history_mgr.append_assistant(text_reply or None, [tc for tc, _ in executed])
        messages.append(
            {
                "role": "assistant",
                "content": text_reply,
                "tool_calls": [serialize_tool_call(tc) for tc, _ in executed],
            }
        )
        for tc, result in executed:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result.output or "",
                }
            )
            self.history_mgr.append_tool_result(tc.id, result.output or "")

    # ---- Main loop ----

    def _run_tool_loop(self, messages: list[dict]) -> None:
        text_reply = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            with yaspin_if_tty():
                response = self.request_mgr.chat(messages)

            choice = response.choices[0]
            msg = choice.message
            text_reply = (msg.content or "").strip()
            tool_calls = msg.tool_calls or []

            if text_reply:
                print_reply(text_reply)

            if not tool_calls:
                self.history_mgr.append_assistant(text_reply or None)
                return

            executed, stopped = self._execute_tools(tool_calls)

            # Always record the tool call and its output, whether or not the
            # loop is about to stop — "stopped" only ends the looping, it
            # doesn't mean the output is thrown away.
            self._record_tool_results(messages, executed, text_reply or "")

            if stopped:
                return

        print_error("Reached maximum tool iterations; stopping.")
        self.history_mgr.append_assistant(text_reply or None)

    # ---- Public API ----

    def run(self, user_input: str) -> None:
        history = self.history_mgr.load()
        self.history_mgr.append_user(user_input)
        messages = self._build_messages(user_input, history)
        self._run_tool_loop(messages)
