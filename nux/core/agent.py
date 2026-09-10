# core/agent.py
# Agentic loop and conversation manager for Nux.

from __future__ import annotations

import json
import signal
from typing import TYPE_CHECKING

from nux.core.constants import SYSTEM_PROMPT
from nux.core.request_manager import RequestManager
from nux.search import BM25Searcher
from nux.storage.history import HistoryManager
from nux.storage.knowledge import KnowledgeManager
from nux.tools import dispatch_tool
from nux.tools.result import ToolResult, serialize_tool_call
from nux.ui.display import print_error, print_info, print_reply

if TYPE_CHECKING:
    from groq.types.chat import ChatCompletionMessageToolCall

    from nux.server.daemon import Session


class _TimeoutError(Exception):
    pass


class Agent:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.history_mgr = HistoryManager(self.session.config.max_history)
        self.knowledge_mgr = KnowledgeManager()
        self.request_mgr = RequestManager(self.session.config)
        self._searcher = BM25Searcher()
        self.last_reply: str = ""

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
        except (json.JSONDecodeError, TypeError):
            return {"_parse_error": tc.function.arguments}

    def _execute_tools(
        self,
        tool_calls: list[ChatCompletionMessageToolCall],
    ) -> tuple[list[tuple[ChatCompletionMessageToolCall, ToolResult]], bool]:

        executed: list[tuple[ChatCompletionMessageToolCall, ToolResult]] = []

        for tc in tool_calls:
            parsed_args = self._parse_tool_args(tc)
            if "_parse_error" in parsed_args:
                result = ToolResult(
                    output=(
                        f"Error: Failed to parse tool arguments as JSON. "
                        f"Raw: {parsed_args['_parse_error']}"
                    ),
                    should_continue=True,
                )
            else:
                result = dispatch_tool(tc.function.name, parsed_args, self.session)
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
        turn = 0

        while True:
            if self.session.max_turns and turn >= self.session.max_turns:
                print_info(f"Reached max turns limit ({self.session.max_turns})")
                return

            self.session.spinner.push("thinking")
            self.session.spinner.start()

            try:
                response = self.request_mgr.chat(messages, self.session.allowed_tools, self.session.spinner)
            finally:
                self.session.spinner.stop()

            choice = response.choices[0]
            msg = choice.message
            text_reply = (msg.content or "").strip()
            tool_calls = msg.tool_calls or []

            if text_reply and not self.session.quiet:
                print_reply(text_reply)

            if not tool_calls:
                if not text_reply and not self.session.quiet:
                    print_info("No response from model. Try providing more context in your prompt.")
                self.history_mgr.append_assistant(text_reply or None)
                self.last_reply = text_reply
                return

            if self.session.dry_run:
                print_info("[dry-run] Agent would execute:")
                for tc in tool_calls:
                    print_info(f"  {tc.function.name}({tc.function.arguments})")
                self.history_mgr.append_assistant(text_reply or None, tool_calls)
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
            turn += 1

            if stopped:
                return

    # -- public API --

    def run(self, user_input: str) -> None:
        if self.session.packet.message.get("resume") and not user_input:
            from nux.storage.db import execute_read

            rows = execute_read(
                "SELECT role, content FROM history ORDER BY id DESC LIMIT 6",
            )
            if not rows:
                print_info("No history to resume.")
                return
            print_info("Resuming from last conversation:")
            for row in reversed(rows):
                role = row["role"]
                content = row["content"] or ""
                if role == "user":
                    print_info(f"  you: {content[:100]}")
                elif role == "assistant":
                    print_info(f"  nux: {content[:100]}")
            return

        history = self.history_mgr.load()
        self.history_mgr.append_user(user_input)
        messages = self._build_messages(user_input, history)

        if self.session.timeout:
            def _timeout_handler(signum: int, frame: object) -> None:
                raise _TimeoutError()

            prev = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(self.session.timeout)
            try:
                self._run_tool_loop(messages)
            except _TimeoutError:
                print_error(f"Timed out after {self.session.timeout}s")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, prev)
        else:
            self._run_tool_loop(messages)
