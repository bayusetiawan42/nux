# tests/test_history.py
# Chat history store tests.

from sharkyo.history import HistoryManager


def test_append_and_load():
    h = HistoryManager()
    h.append_user("kompres folder ini")
    h.append_assistant("Siap.")
    msgs = h.load()
    assert [(m["role"], m.get("content")) for m in msgs] == [
        ("user", "kompres folder ini"),
        ("assistant", "Siap."),
    ]


def test_tool_call_roundtrip():
    h = HistoryManager()
    h.append_assistant(
        None,
        tool_calls=[
            {"id": "call_1", "type": "function", "function": {"name": "CMD", "arguments": "{}"}}
        ],
    )
    h.append_tool_result("call_1", "output text")
    msgs = h.load()
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "CMD"
    assert msgs[1]["tool_call_id"] == "call_1"
    assert msgs[1]["content"] == "output text"


def test_empty_assistant_not_recorded():
    h = HistoryManager()
    h.append_assistant(None)
    assert h.load() == []


def test_clear():
    h = HistoryManager()
    h.append_user("a")
    h.clear()
    assert h.load() == []


def test_window_trims_incomplete_tool_exchange_at_head():
    # A sliced window must not start with a bare tool message whose
    # assistant tool_call fell outside the retained window.
    h = HistoryManager(max_messages=2)
    for i in range(5):
        h.append_user(f"turn {i}")
    h.append_assistant(
        None,
        tool_calls=[
            {"id": "c1", "type": "function", "function": {"name": "CMD", "arguments": "{}"}}
        ],
    )
    h.append_tool_result("c1", "out")
    msgs = h.load()
    assert msgs == [
        {"role": "assistant", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "CMD", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "out"},
    ]


def test_window_drops_orphan_tool_message():
    # A run that crashed mid-exchange can leave a bare tool row whose
    # assistant tool_call lies outside the retained window. It must be
    # dropped rather than sent to the API.
    h = HistoryManager(max_messages=1)
    h.append_user("boundary")
    h.append_assistant(
        None,
        tool_calls=[
            {"id": "c1", "type": "function", "function": {"name": "CMD", "arguments": "{}"}}
        ],
    )
    h.append_tool_result("c1", "out")
    assert h.load() == []