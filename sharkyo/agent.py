# agent.py
# Agentic loop and conversation manager for Sharkyo.

import json

from openai.types.chat import ChatCompletionMessageToolCall
from yaspin import yaspin

from sharkyo.config import Config, load_config
from sharkyo.constants import SYSTEM_PROMPT
from sharkyo.context import get_environment_context
from sharkyo.display import SHARK_SPINNER, print_error, print_reply
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager
from sharkyo.request_manager import RequestManager
from sharkyo.search import BM25Searcher
from sharkyo.tools import dispatch_tool
from sharkyo.tools.result import ToolResult

# Safety cap: stop the tool loop after this many rounds per user turn.
MAX_TOOL_ITERATIONS = 10


class Agent:
    # Core Sharkyo AI agent: executes multi-turn reasoning and tool invocation.

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self.history_mgr = HistoryManager(self.config.max_history)
        self.knowledge_mgr = KnowledgeManager()
        self.request_mgr = RequestManager(self.config)
        self._searcher = BM25Searcher()

    def _build_system_prompt(self) -> str:
        # Build the full system prompt by injecting user knowledge and
        # live environment context as XML blocks appended to the base prompt.
        prompt = SYSTEM_PROMPT

        entries = self.knowledge_mgr.list_all()
        if entries:
            block = "\n".join(f"{k} = {v}" for k, v in entries)
            prompt += f"\n\n<user_knowledge>\n{block}\n</user_knowledge>"

        prompt += f"\n\n<environment_context>\n{get_environment_context()}\n</environment_context>"
        return prompt

    def _build_skill_hint(self, user_input: str) -> str | None:
        # Search skills relevant to the user input and return a hint string,
        # or None if no strong matches were found.
        results = self._searcher.search(user_input, top_k=3)
        if not results:
            return None
        names = ", ".join(f"'{r.name}'" for r in results)
        return f"[Relevant skills: {names}. Consider calling SKILL with one of these before acting.]"

    def _serialize_tool_call(self, tc: ChatCompletionMessageToolCall) -> dict:
        # Convert an SDK tool call into a plain API-ready dict.
        return {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }

    def _parse_tool_args(self, tc: ChatCompletionMessageToolCall) -> dict:
        # Parse a tool call's JSON arguments, falling back to {} on malformed input.
        try:
            return json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            return {}

    def run(self, user_input: str) -> None:
        # Execute the agentic turn for a given user prompt.
        # Runs the tool loop until the model stops requesting tools,
        # a tool signals that the loop should stop, or the iteration cap is hit.
        history = self.history_mgr.load()
        self.history_mgr.append_user(user_input)

        skill_hint = self._build_skill_hint(user_input)
        augmented_input = f"{skill_hint}\n\n{user_input}" if skill_hint else user_input

        messages: list[dict] = (
            [{"role": "system", "content": self._build_system_prompt()}]
            + history
            + [{"role": "user", "content": augmented_input}]
        )

        for _ in range(MAX_TOOL_ITERATIONS):
            with yaspin(SHARK_SPINNER):
                response = self.request_mgr.chat(messages)

            choice = response.choices[0]
            msg = choice.message
            text_reply = (msg.content or "").strip()
            tool_calls = msg.tool_calls or []

            if text_reply:
                print_reply(text_reply)

            # No tools requested — turn is complete.
            if not tool_calls:
                self.history_mgr.append_assistant(text_reply or None)
                return

            # Execute each requested tool in order, stopping on the first
            # tool that signals the loop should end (e.g. user cancelled CMD).
            executed: list[tuple[ChatCompletionMessageToolCall, ToolResult]] = []
            stopped = False
            for tc in tool_calls:
                result: ToolResult = dispatch_tool(tc.function.name, self._parse_tool_args(tc), self.config)
                executed.append((tc, result))
                if not result.should_continue:
                    stopped = True
                    break

            if stopped:
                # Tool signalled stop (e.g. user cancelled CMD, or unknown tool).
                if text_reply:
                    self.history_mgr.append_assistant(text_reply)
                return

            # Record the assistant turn (with tool_calls) and each tool result,
            # then loop back so the model can react to the tool output.
            self.history_mgr.append_assistant(text_reply or None, [tc for tc, _ in executed])
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [self._serialize_tool_call(tc) for tc, _ in executed],
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

        print_error("Reached maximum tool iterations; stopping.")
        self.history_mgr.append_assistant(text_reply or None)