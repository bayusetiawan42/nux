# core/agent.py
# Agentic loop and conversation manager for Nux.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from nux.core.constants import SYSTEM_PROMPT
from nux.core.request_manager import RequestManager
from nux.search import BM25Searcher
from nux.storage.history import HistoryManager
from nux.storage.knowledge import KnowledgeManager
from nux.tools import dispatch_tool
from nux.tools.result import ToolResult, serialize_tool_call
from nux.ui.display import print_error, print_info, print_reply, yaspin_if_tty

if TYPE_CHECKING:
    from groq.types.chat import ChatCompletionMessageToolCall

    from nux.server.daemon import Session


class Agent:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.history_mgr = HistoryManager(self.session.config.max_history)
        self.knowledge_mgr = KnowledgeManager()
        self.request_mgr = RequestManager(self.session.config)
        self._searcher = BM25Searcher()

    # -- prompt construction --

    def _build_system_prompt(self) -> str:
        entries = self.knowledge_mgr.list_all()
        env_ctx = self.session.get_environment_context()

        if entries:
            knowledges = "\n".join(f"{k} = {v}" for k, v in entries)
        else:
            knowledges = "No knowledges is stored."

        system_prompt = (
            f"<system_prompt>\n{SYSTEM_PROMPT}\n</system_prompt>\n\n"
            f"<knowledge>\n{knowledges or None}\n</knowledge>\n\n"
            f"<environment_context>\n{env_ctx}\n</environment_context>"
        )

        return system_prompt

    def _build_messages(self, user_input: str, history: list[dict]) -> list[dict]:
        return (
            [{"role": "system", "content": self._build_system_prompt()}]
            + history
            + [{"role": "user", "content": user_input}]
        )

    # -- tool helpers --

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
            result = dispatch_tool(tc.function.name, self._parse_tool_args(tc), self.session)
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

    # -- main loop --

    def _run_tool_loop(self, messages: list[dict]) -> None:
        text_reply = ""

        while True:
            with yaspin_if_tty():
                response = self.request_mgr.chat(messages)

            choice = response.choices[0]
            msg = choice.message
            text_reply = (msg.content or "").strip()
            tool_calls = msg.tool_calls or []

            if text_reply and not self.session.quiet:
                print_reply(text_reply)

            if not tool_calls:
                self.history_mgr.append_assistant(text_reply or None)
                return

            if self.session.verbose:
                for tc in tool_calls:
                    print_info(f"tool_call: {tc.function.name}({tc.function.arguments})")

            executed, stopped = self._execute_tools(tool_calls)

            if self.session.verbose:
                for tc, result in executed:
                    output_preview = (result.output or "")[:200]
                    print_info(f"tool_result: {tc.function.name} -> {output_preview}")

            # Always record the tool call and its output, whether or not the
            # loop is about to stop -- "stopped" only ends the looping, it
            # doesn't mean the output is thrown away.
            self._record_tool_results(messages, executed, text_reply or "")

            if stopped:
                return

    # -- public API --

    def run(self, user_input: str) -> None:
        history = self.history_mgr.load()
        self.history_mgr.append_user(user_input)
        messages = self._build_messages(user_input, history)
        self._run_tool_loop(messages)
