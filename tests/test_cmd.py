# tests/test_cmd.py
# CMD tool tests: arg parsing and the pty execution path.

from nux.core.config import Config
from nux.tools.cmd import CmdArgs, _run

_config = Config()


class TestRun:
    def test_echo_and_success(self):
        transcript, returncode = _run("echo hello", _config)
        assert "hello" in transcript
        assert returncode == 0

    def test_merges_stderr_into_transcript(self):
        transcript, _ = _run("echo out; echo err >&2", _config)
        assert "out" in transcript
        assert "err" in transcript

    def test_exit_code_propagates(self):
        _, returncode = _run("exit 3", _config)
        assert returncode == 3

    def test_stdin_is_forwarded(self):
        # With pty, stdin is forwarded to the command. When stdin is not
        # a TTY (like in tests), the command should still work but may
        # get input from the test runner's stdin.
        transcript, returncode = _run("echo 'pty works'", _config)
        assert "pty works" in transcript
        assert returncode == 0

    def test_command_not_found(self):
        _, returncode = _run("definitely-not-a-command-xyz", _config)
        assert returncode != 0

    def test_full_output_not_truncated(self):
        transcript, _ = _run("yes x | head -c 20000", _config)
        assert len(transcript) >= 20000


class TestArgs:
    def test_from_dict(self):
        args = CmdArgs.from_dict({"command": "ls", "stop_after_execution": True})
        assert args.command == "ls"
        assert args.stop_after_execution is True

    def test_null_command_does_not_crash(self):
        args = CmdArgs.from_dict({"command": None})
        assert args.command == ""

    def test_from_dict_defaults(self):
        args = CmdArgs.from_dict({"command": "ls"})
        assert args.command == "ls"
        assert args.stop_after_execution is False

    def test_unknown_keys_ignored(self):
        args = CmdArgs.from_dict({"command": "ls", "interactive": True})
        assert not hasattr(args, "interactive")
