# tests/test_cli.py
# CLI parser tests (no side effects — parsing only).

import pytest

from sharkyo.cli import parse


def test_prompt_alone():
    args = parse(["compress", "this", "folder"])
    assert args.prompt == ["compress", "this", "folder"]
    assert not args.keys


def test_prompt_with_flag():
    args = parse(["summarize", "git", "log", "--knowledge"])
    assert args.prompt == ["summarize", "git", "log"]
    assert args.knowledge is True


def test_flag_first_then_prompt():
    args = parse(["--keys", "list", "my", "files"])
    assert args.keys is True
    assert args.prompt == ["list", "my", "files"]


def test_add_key_options():
    args = parse(["--add-key", "gsk_x", "--base-url", "https://api.example.com"])
    assert args.add_key == "gsk_x"
    assert args.base_url == "https://api.example.com"


def test_empty_prompt_defaults():
    args = parse([])
    assert args.prompt == []
    assert args.clear is False
    assert args.add_key is None


def test_multiple_flags_combined():
    args = parse(["--clear", "--clear-knowledge"])
    assert args.clear is True
    assert args.clear_knowledge is True
    assert args.prompt == []


def test_double_dash_separator():
    args = parse(["--clear", "--", "how much battery do I have left?"])
    assert args.clear is True
    assert args.prompt == ["how much battery do I have left?"]


def test_double_dash_only():
    args = parse(["--clear", "--"])
    assert args.clear is True
    assert args.prompt == []


def test_command_subcommand():
    args = parse(["command", "keys"])
    assert args.prompt == ["command", "keys"]


def test_command_subcommand_with_args():
    args = parse(["command", "delete-knowledge", "mykey"])
    assert args.prompt == ["command", "delete-knowledge", "mykey"]


def test_server_subcommand():
    args = parse(["server", "status"])
    assert args.prompt == ["server", "status"]


def test_delete_knowledge_option():
    args = parse(["--delete-knowledge", "mykey"])
    assert args.delete_knowledge == "mykey"
    assert args.prompt == []


def test_all_flags():
    args = parse(["--keys", "--clear", "--knowledge", "--clear-knowledge"])
    assert args.keys is True
    assert args.clear is True
    assert args.knowledge is True
    assert args.clear_knowledge is True
    assert args.prompt == []


def test_unknown_flag_exits():
    with pytest.raises(SystemExit):
        parse(["--unknown"])


def test_add_key_missing_value_exits():
    with pytest.raises(SystemExit):
        parse(["--add-key"])


def test_help_flag(capsys):
    with pytest.raises(SystemExit):
        parse(["--help"])
    captured = capsys.readouterr()
    assert "Usage:" in captured.out
    assert "Commands:" in captured.out
    assert "Options:" in captured.out
    assert "Examples:" in captured.out
