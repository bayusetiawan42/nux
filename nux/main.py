# main.py
# Nux - main CLI entry point.

import json
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
        agent = Agent(session)
        agent.run(prompt)

        if flags.get("json_output"):
            output = {
                "reply": agent.last_reply,
                "model": session.config.model,
                "dry_run": session.dry_run,
            }
            print(json.dumps(output, ensure_ascii=False))

    except NuxError as e:
        log_error(e, context=f"prompt={prompt!r}")
        if flags.get("json_output"):
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            from nux.ui.display import print_error

            print_error(str(e))
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        log_error(e, context=f"prompt={prompt!r}")
        if flags.get("json_output"):
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            from nux.ui.display import print_error

            print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
