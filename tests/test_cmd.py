# tests/test_cmd.py
# CMD tool tests: bounded tail buffer and the pty execution path.

import os
import sys
import time

from sharkyo.config import Config
from sharkyo.tools.cmd import CmdArgs, _run_pty, _Tail, _truncate


class TestTailBuffer:
    def test_keeps_only_last_bytes(self):
        tail = _Tail(10)
        tail.append(b"abcdefghijklmno")
        assert tail.text() == "fghijklmno"

    def test_no_overflow_for_small_input(self):
        tail = _Tail(5)
        tail.append(b"ab")
        tail.append(b"cd")
        assert tail.text() == "abcd"

    def test_appends_across_chunks(self):
        tail = _Tail(6)
        tail.append(b"abc")
        tail.append(b"def")
        tail.append(b"gh")
        assert tail.text() == "cdefgh"

    def test_single_oversized_chunk(self):
        tail = _Tail(4)
        tail.append(b"abcdefgh")
        assert tail.text() == "efgh"

    def test_zero_limit_keeps_nothing(self):
        tail = _Tail(0)
        tail.append(b"data")
        assert tail.text() == ""


class TestPtyRunner:
    def test_echo_and_success(self):
        result = _run_pty("echo hello", 1000, stream=False)
        assert result.stdout.strip() == "hello"
        assert result.returncode == 0
        assert not result.timed_out

    def test_merges_stderr_into_transcript(self):
        result = _run_pty("echo out; echo err >&2", 1000, stream=False)
        assert "out" in result.stdout
        assert "err" in result.stdout

    def test_exit_code_propagates(self):
        result = _run_pty("exit 3", 1000, stream=False)
        assert result.returncode == 3

    def test_transcript_capped_to_tail(self):
        result = _run_pty("yes x | head -c 20000", 120, stream=False)
        assert len(result.stdout) <= 120
        assert "x" in result.stdout

    def test_timeout_kills_command(self):
        result = _run_pty("sleep 5", 1000, stream=False, timeout=0.4)
        assert result.timed_out
        assert result.returncode != 0

    def test_command_not_found(self):
        result = _run_pty("definitely-not-a-command-xyz", 1000, stream=False)
        assert result.returncode == 127

    def test_forwards_stdin_when_tty(self):
        # When the caller's stdin is a real terminal, bytes typed there are
        # forwarded into the child so prompt-based commands (sudo, read)
        # can be answered.
        master, slave = os.openpty()
        pid = os.fork()
        if pid == 0:
            os.setsid()
            os.close(master)
            os.dup2(slave, 0)
            os.close(slave)
            os.execve(
                sys.executable,
                [
                    sys.executable,
                    "-c",
                    (
                        "import os\n"
                        "from sharkyo.config import Config\n"
                        "from sharkyo.tools.cmd import _run_pty\n"
                        "r = _run_pty('read -p X n; echo got:$n', 1000, stream=False)\n"
                        "print('TRANSCRIPT', repr(r.stdout), flush=True)\n"
                    ),
                ],
                dict(os.environ),
            )
        os.close(slave)
        time.sleep(0.3)
        os.write(master, b"Luigi\n")
        time.sleep(0.5)
        os.close(master)
        _, st = os.waitpid(pid, 0)
        # Child exits 0 if the inner read consumed the forwarded input.
        assert os.waitstatus_to_exitcode(st) == 0


class TestArgs:
    def test_from_dict(self):
        args = CmdArgs.from_dict(
            {"command": "ls", "review_output": True, "review_output_stderr": True}
        )
        assert args.command == "ls"
        assert args.review_output is True
        assert args.review_output_stderr is True

    def test_from_dict_defaults(self):
        args = CmdArgs.from_dict({"command": "ls"})
        assert args.command == "ls"
        assert args.review_output is False
        assert args.review_output_stderr is False

    def test_unknown_keys_ignored(self):
        args = CmdArgs.from_dict({"command": "ls", "interactive": True})
        assert not hasattr(args, "interactive")


class TestTruncate:
    def test_short_text_untouched(self):
        assert _truncate("hello", 3000) == "hello"

    def test_long_text_keeps_tail(self):
        text = _truncate("a" * 3000, 30)
        assert "a" * 10 in text
        assert text.endswith("a" * 20)
        assert "truncated" in text
        assert len(text) < 100


def test_default_config_sane():
    cfg = Config()
    assert cfg.cmd_out_chars > 0
    assert cfg.cmd_timeout >= 0