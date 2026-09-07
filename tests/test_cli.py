# tests/test_cli.py
# CLI parser tests (no side effects — parsing only).

from sharkyo.cli import build_parser


def test_prompt_alone():
    args = build_parser().parse_args(["compress", "this", "folder"])
    assert args.prompt == ["compress", "this", "folder"]
    assert not args.keys


def test_prompt_with_flag():
    args = build_parser().parse_args(["summarize", "git", "log", "--knowledge"])
    assert args.prompt == ["summarize", "git", "log"]
    assert args.knowledge is True


def test_flag_first_then_prompt():
    args = build_parser().parse_args(["--keys", "list", "my", "files"])
    assert args.keys is True
    assert args.prompt == ["list", "my", "files"]


def test_add_key_options():
    args = build_parser().parse_args(
        ["--add-key", "gsk_x", "--provider", "openai", "--base-url", "https://api.example.com"]
    )
    assert args.add_key == "gsk_x"
    assert args.provider == "openai"
    assert args.base_url == "https://api.example.com"


def test_empty_prompt_defaults():
    args = build_parser().parse_args([])
    assert args.prompt == []
    assert args.clear is False
    assert args.add_key is None


def test_multiple_flags_combined():
    args = build_parser().parse_args(["--clear", "--clear-knowledge"])
    assert args.clear is True
    assert args.clear_knowledge is True
    assert args.prompt == []


def test_double_dash_separator():
    args = build_parser().parse_args(["--clear", "--", "baterai ku sisa berapa?"])
    assert args.clear is True
    assert args.prompt == ["baterai ku sisa berapa?"]


def test_double_dash_only():
    args = build_parser().parse_args(["--clear", "--"])
    assert args.clear is True
    assert args.prompt == []


def test_command_subcommand():
    args = build_parser().parse_args(["command", "keys"])
    assert args.prompt == ["command", "keys"]


def test_command_subcommand_with_args():
    args = build_parser().parse_args(["command", "delete-knowledge", "mykey"])
    assert args.prompt == ["command", "delete-knowledge", "mykey"]


def test_server_subcommand():
    args = build_parser().parse_args(["server", "status"])
    assert args.prompt == ["server", "status"]