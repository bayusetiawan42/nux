# tests/test_cli.py
# CLI parser tests (no side effects -- parsing only).

import pytest

from nux.cli import parse


def test_prompt_alone():
    args = parse(["compress", "this", "folder"])
    assert args.prompt == ["compress", "this", "folder"]


def test_prompt_with_flag():
    args = parse(["summarize", "git", "log", "--knowledge"])
    assert args.prompt == ["summarize", "git", "log"]
    assert args.knowledge is True


def test_flag_first_then_prompt():
    args = parse(["--stats", "list", "my", "files"])
    assert args.stats == "list"
    assert args.prompt == ["my", "files"]


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
    args = parse(["command", "clear"])
    assert args.prompt == ["command", "clear"]


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
    args = parse(["--stats", "--clear", "--knowledge", "--clear-knowledge"])
    assert args.stats == ""
    assert args.clear is True
    assert args.knowledge is True
    assert args.clear_knowledge is True
    assert args.prompt == []


def test_stats_flag():
    args = parse(["--stats"])
    assert args.stats == ""


def test_stats_with_index():
    args = parse(["--stats", "2"])
    assert args.stats == "2"


def test_stats_equals_syntax():
    args = parse(["--stats=3"])
    assert args.stats == "3"


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
    assert "--" in captured.out


def test_version_flag(capsys):
    with pytest.raises(SystemExit):
        parse(["--version"])
    captured = capsys.readouterr()
    assert "nux" in captured.out


def test_version_short_flag(capsys):
    with pytest.raises(SystemExit):
        parse(["-v"])
    captured = capsys.readouterr()
    assert "nux" in captured.out


def test_no_color_flag():
    args = parse(["--no-color", "hello"])
    assert args.no_color is True
    assert args.prompt == ["hello"]


def test_verbose_flag():
    args = parse(["-V", "hello"])
    assert args.verbose is True
    assert args.prompt == ["hello"]


def test_verbose_long_flag():
    args = parse(["--verbose", "hello"])
    assert args.verbose is True


def test_quiet_flag():
    args = parse(["-q", "hello"])
    assert args.quiet is True
    assert args.prompt == ["hello"]


def test_quiet_long_flag():
    args = parse(["--quiet", "hello"])
    assert args.quiet is True


def test_new_flags_defaults():
    args = parse([])
    assert args.version is False
    assert args.no_color is False
    assert args.verbose is False
    assert args.quiet is False


def test_new_flags_combined():
    args = parse(["--no-color", "--verbose", "--quiet", "hello"])
    assert args.no_color is True
    assert args.verbose is True
    assert args.quiet is True
    assert args.prompt == ["hello"]


def test_config_subcommand():
    args = parse(["config", "get", "model"])
    assert args.prompt == ["config", "get", "model"]


def test_config_subcommand_no_args():
    args = parse(["config"])
    assert args.prompt == ["config"]


def test_skills_subcommand():
    args = parse(["skills"])
    assert args.prompt == ["skills"]


def test_skills_search_subcommand():
    args = parse(["skills", "search", "network"])
    assert args.prompt == ["skills", "search", "network"]


def test_logs_subcommand():
    args = parse(["logs"])
    assert args.prompt == ["logs"]


def test_logs_clear_subcommand():
    args = parse(["logs", "clear"])
    assert args.prompt == ["logs", "clear"]


def test_doctor_subcommand():
    args = parse(["doctor"])
    assert args.prompt == ["doctor"]


def test_dry_run_flag():
    args = parse(["-n", "hello"])
    assert args.dry_run is True
    assert args.prompt == ["hello"]


def test_dry_run_long_flag():
    args = parse(["--dry-run", "hello"])
    assert args.dry_run is True


def test_resume_flag():
    args = parse(["-r"])
    assert args.resume is True
    assert args.prompt == []


def test_resume_long_flag():
    args = parse(["--resume"])
    assert args.resume is True


def test_sessions_flag():
    args = parse(["--sessions"])
    assert args.sessions is True
    assert args.prompt == []


def test_json_flag():
    args = parse(["--json", "hello"])
    assert args.json_output is True
    assert args.prompt == ["hello"]


def test_timeout_flag():
    args = parse(["--timeout", "30", "hello"])
    assert args.timeout == 30
    assert args.prompt == ["hello"]


def test_timeout_invalid_exits():
    with pytest.raises(SystemExit):
        parse(["--timeout", "abc"])


def test_timeout_missing_value_exits():
    with pytest.raises(SystemExit):
        parse(["--timeout"])


def test_medium_flags_defaults():
    args = parse([])
    assert args.dry_run is False
    assert args.resume is False
    assert args.sessions is False
    assert args.json_output is False
    assert args.timeout is None


def test_medium_flags_combined():
    args = parse(["--dry-run", "--resume", "--json", "--timeout", "10", "hello"])
    assert args.dry_run is True
    assert args.resume is True
    assert args.json_output is True
    assert args.timeout == 10
    assert args.prompt == ["hello"]


def test_sessions_subcommand():
    args = parse(["sessions"])
    assert args.prompt == ["sessions"]


def test_max_turns_flag():
    args = parse(["--max-turns", "5", "hello"])
    assert args.max_turns == 5
    assert args.prompt == ["hello"]


def test_max_turns_invalid_exits():
    with pytest.raises(SystemExit):
        parse(["--max-turns", "abc"])


def test_max_turns_missing_value_exits():
    with pytest.raises(SystemExit):
        parse(["--max-turns"])


def test_no_confirm_flag():
    args = parse(["--no-confirm", "hello"])
    assert args.no_confirm is True
    assert args.prompt == ["hello"]


def test_tool_flag():
    args = parse(["--tool", "cmd,knowledge", "hello"])
    assert args.tools == "cmd,knowledge"
    assert args.prompt == ["hello"]


def test_tool_missing_value_exits():
    with pytest.raises(SystemExit):
        parse(["--tool"])


def test_remove_key_flag():
    args = parse(["--remove-key", "2"])
    assert args.remove_key == "2"


def test_remove_key_missing_value_exits():
    with pytest.raises(SystemExit):
        parse(["--remove-key"])


def test_breaking_flags_defaults():
    args = parse([])
    assert args.max_turns is None
    assert args.no_confirm is False
    assert args.tools is None
    assert args.remove_key is None


def test_breaking_flags_combined():
    args = parse(["--max-turns", "3", "--no-confirm", "--tool", "cmd", "hello"])
    assert args.max_turns == 3
    assert args.no_confirm is True
    assert args.tools == "cmd"
    assert args.prompt == ["hello"]
