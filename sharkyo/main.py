# main.py
# Sharkyo — main CLI entry point.

import sys

from sharkyo.cli import main as run_cli
from sharkyo.constants import setup_dirs
from sharkyo.display import print_error
from sharkyo.request_manager import SharkyoError


def main() -> None:
    # Parse CLI input and run Sharkyo.
    setup_dirs()
    prompt = run_cli()

    # Fast path: hand the prompt to the background daemon (warm imports, warm
    # DB). Falls back to running in-process when the daemon is unavailable.
    from sharkyo.client import run_remote

    exit_code = run_remote(prompt)
    if exit_code is not None:
        sys.exit(exit_code)

    try:
        from sharkyo.agent import Agent

        Agent().run(prompt)
    except SharkyoError as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()