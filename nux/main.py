# main.py
# Nux - main CLI entry point.

import sys

from nux.cli import main as run_cli, get_flags
from nux.core.constants import setup_dirs
from nux.core.errors import NuxError


def main() -> None:
    setup_dirs()
    prompt = run_cli()
    flags = get_flags()

    if flags.get("no_color"):
        from nux.ui.display import set_no_color

        set_no_color()

    from nux.server.client import run_remote

    exit_code = run_remote(prompt, flags)

    if exit_code is not None:
        sys.exit(exit_code)

    try:
        from nux.core.agent import Agent
        from nux.core.error_logger import log_error
        from nux.server.daemon import Session

        session = Session.create(prompt, flags=flags)
        Agent(session).run(prompt)
    except NuxError as e:
        log_error(e, context=f"prompt={prompt!r}")
        from nux.ui.display import print_error

        print_error(str(e))
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        log_error(e, context=f"prompt={prompt!r}")
        from nux.ui.display import print_error

        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
