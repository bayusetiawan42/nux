"""Agentic loop and conversation manager for Sharkyo."""

import json
from yaspin import yaspin

from sharkyo.config import Config, load_config
from sharkyo.constants import SYSTEM_PROMPT
from sharkyo.display import SHARK_SPINNER, print_reply
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager
from sharkyo.request_manager import RequestManager
from sharkyo.tools import dispatch_tool


class Agent:
    """Core Sharkyo AI agent executing multi-turn reasoning and tool invocation."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self.history_mgr = HistoryManager(self.config.max_history)
        self.knowledge_mgr = KnowledgeManager()
        self.request_mgr = RequestManager(self.config)

    def build_system_prompt(self) -> str:
        """Inject long-term knowledge facts into the system prompt."""
        prompt = SYSTEM_PROMPT
        entries = self.knowledge_mgr.list_all()
        if entries:
            block = "\n".join(f"{k} = {v}" for k, v in entries)
            prompt += f"\nWhat you know about the user:\n{block}"
        return prompt

    def run(self, user_input: str) -> None:
        """Execute the agentic turn for a given user prompt."""
        history = self.history_mgr.load()
        self.history_mgr.append_user(user_input)

        messages = (
            [{"role": "system", "content": self.build_system_prompt()}]
            + history
            + [{"role": "user", "content": user_input}]
        )

        while True:
            with yaspin(SHARK_SPINNER):
                response = self.request_mgr.chat(messages)

            choice = response.choices[0]
            msg = choice.message
            text_reply = (msg.content or "").strip()
            tool_calls = msg.tool_calls or []

            if text_reply:
                print_reply(text_reply)

            # If no tools requested, finish turn
            if not tool_calls:
                self.history_mgr.append_assistant(text_reply or None)
                break

            tc = tool_calls[0]
            name = tc.function.name
            try:
                f_args = json.loads(tc.function.arguments)
            except Exception:
                f_args = {}

            tool_output, should_continue = dispatch_tool(name, f_args, self.config)

            # If loop should not continue (command cancelled, or no review needed):
            if not should_continue:
                if text_reply:
                    self.history_mgr.append_assistant(text_reply)
                break

            # If continuing: record assistant tool_calls and tool output in messages and history
            self.history_mgr.append_assistant(text_reply or None, tool_calls)
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                ],
            })

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_output or "",
            }
            messages.append(tool_msg)
            self.history_mgr.append_tool_result(tc.id, tool_output or "")
