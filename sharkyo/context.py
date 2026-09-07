# context.py
# Collects live environment information to inject into the system prompt.

import os
import subprocess
from datetime import datetime


def _run_git(args: list[str]) -> str:
    # Run a git command and return stripped stdout, or empty string on failure.
    try:
        return subprocess.check_output(
            ["git"] + args,
            stderr=subprocess.DEVNULL,
            timeout=0.2,
        ).decode("utf-8").strip()
    except Exception:
        return ""


def get_environment_context() -> str:
    # Build a string describing the current runtime environment.
    # Includes CWD, timestamp, and optional git remote/branch if inside a repo.
    cwd = os.getcwd()
    git_remote = _run_git(["config", "--get", "remote.origin.url"])
    git_branch = _run_git(["branch", "--show-current"])

    lines = [
        f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Working Directory (CWD): {cwd}",
    ]

    if git_remote:
        lines.append(f"Git Remote (origin): {git_remote}")
    if git_branch:
        lines.append(f"Git Branch: {git_branch}")

    return "\n".join(lines)
