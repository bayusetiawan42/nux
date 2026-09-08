# core/context.py
# Collects live environment information to inject into the system prompt.

import os
import subprocess
from datetime import datetime


def _run_git(args: list[str]) -> str:
    try:
        return (
            subprocess.check_output(
                ["git"] + args,
                stderr=subprocess.DEVNULL,
                timeout=0.2,
            )
            .decode("utf-8")
            .strip()
        )
    except (subprocess.SubprocessError, OSError):
        return ""


def get_environment_context() -> str:
    cwd = os.getcwd()
    git_remote = _run_git(["config", "--get", "remote.origin.url"])
    git_branch = _run_git(["branch", "--show-current"])

    lines = [
        f"Current Time: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Working Directory (CWD): {cwd}",
    ]

    if git_remote:
        lines.append(f"Git Remote (origin): {git_remote}")
    if git_branch:
        lines.append(f"Git Branch: {git_branch}")

    return "\n".join(lines)
