# tests/test_cmd.py
# CMD tool tests: arg parsing and the subprocess execution path.

from sharkyo.tools.cmd import CmdArgs, _run


class TestRun:
    def test_echo_and_success(self):
        transcript, returncode = _run("echo hello")
        assert transcript.strip() == "hello"
        assert returncode == 0

    def test_merges_stderr_into_transcript(self):
        transcript, _ = _run("echo out; echo err >&2")
        assert "out" in transcript
        assert "err" in transcript

    def test_exit_code_propagates(self):
        _, returncode = _run("exit 3")
        assert returncode == 3

    def test_stdin_is_ignored(self):
        # stdin is DEVNULL, so a command reading from it should get EOF
        # immediately rather than hanging or picking up our test runner's stdin.
        transcript, returncode = _run("cat")
        assert transcript == ""
        assert returncode == 0

    def test_command_not_found(self):
        _, returncode = _run("definitely-not-a-command-xyz")
        assert returncode != 0

    def test_full_output_not_truncated(self):
        transcript, _ = _run("yes x | head -c 20000")
        assert len(transcript) == 20000


class TestArgs:
    def test_from_dict(self):
        args = CmdArgs.from_dict({"command": "ls", "stop_after_execution": True})
        assert args.command == "ls"
        assert args.stop_after_execution is True

    def test_from_dict_defaults(self):
        args = CmdArgs.from_dict({"command": "ls"})
        assert args.command == "ls"
        assert args.stop_after_execution is False

    def test_unknown_keys_ignored(self):
        args = CmdArgs.from_dict({"command": "ls", "interactive": True})
        assert not hasattr(args, "interactive")
