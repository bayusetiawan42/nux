"""Sharkyo — main agentic loop entry point."""

import json
import sys

from yaspin import yaspin

from sharkyo.cli import handle_flags
from sharkyo.constants import SYSTEM_PROMPT
from sharkyo.display import print_reply, SHARK_SPINNER
from sharkyo.history import HistoryManager
from sharkyo.knowledge import KnowledgeManager
from sharkyo.rcfiles import load_rc, rc_int
from sharkyo.request_manager import RequestManager
from sharkyo.tool_runner import run_tool


def _build_system_prompt() -> str:
    """Build system prompt, injecting stored knowledge if available."""
    prompt = SYSTEM_PROMPT
    entries = KnowledgeManager().list_all()
    if entries:
        block = "\n".join(f"{k} = {v}" for k, v in entries)
        prompt += f"\nWhat you know about the user:\n{block}"
    return prompt


def main() -> None:
    args = sys.argv[1:]
    handle_flags(args)

    # Collect non-flag positional args as user input
    skip_next = False
    user_parts = []
    flag_with_value = {
        "--add-key", "--provider", "--base-url", "--delete-knowledge"
    }
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in flag_with_value:
            i += 2  # skip flag and its value
            continue
        if arg.startswith("-"):
            i += 1
            continue
        user_parts.append(arg)
        i += 1

    user_input = " ".join(user_parts).strip()
    if not user_input:
        from sharkyo.cli import _print_help
        _print_help()
        sys.exit(0)


    rc = load_rc()
    history_mgr = HistoryManager(rc_int(rc, "max_history"))
    req_mgr = RequestManager()

    history = history_mgr.load()
    history_mgr.append_user(user_input)

    messages = (
        [{"role": "system", "content": _build_system_prompt()}]
        + history
        + [{"role": "user", "content": user_input}]
    )

    while True:
        with yaspin(SHARK_SPINNER):
            response = req_mgr.chat(messages)

        msg = response.choices[0].message
        text_reply = (msg.content or "").strip()
        tool_calls = msg.tool_calls or []

        if text_reply:
            print_reply(text_reply)

        if not tool_calls:
            history_mgr.append_assistant(text_reply or None)
            break

        tc = tool_calls[0]
        name = tc.function.name
        f_args = json.loads(tc.function.arguments)

        # Save assistant message with clean tool_calls (no pydantic objects)
        history_mgr.append_assistant(text_reply or None, tool_calls)
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

        tool_output, should_continue = run_tool(name, f_args)

        if not should_continue:
            break

        tool_msg = {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": tool_output,
        }
        messages.append(tool_msg)
        history_mgr.append_tool_result(tc.id, tool_output)
