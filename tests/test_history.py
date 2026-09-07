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