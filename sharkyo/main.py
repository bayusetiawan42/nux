# main.py
# Sharkyo — main CLI entry point.

import sys

from sharkyo.agent import Agent
from sharkyo.cli import main as run_cli
from sharkyo.constants import setup_dirs
from sharkyo.display import print_error
from sharkyo.request_manager import SharkyoError


def main() -> None:
    # Parse CLI input and run Sharkyo.
    setup_dirs()
    prompt = run_cli()
    try:
        Agent().run(prompt)
    except SharkyoError as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()