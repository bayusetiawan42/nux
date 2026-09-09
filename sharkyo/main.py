# main.py
# Sharkyo - main CLI entry point.

import sys

from sharkyo.cli import main as run_cli
from sharkyo.core.constants import setup_dirs
from sharkyo.core.errors import SharkyoError


def main() -> None:
    setup_dirs()
    prompt = run_cli()

    from sharkyo.server.client import run_remote

    exit_code = run_remote(prompt)

    if exit_code is not None:
        sys.exit(exit_code)

    try:
        from sharkyo.core.agent import Agent
        from sharkyo.server.daemon import Session

        session = Session.create(prompt)
        Agent(session).run(prompt)
    except SharkyoError as e:
        from sharkyo.ui.display import print_error

        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
