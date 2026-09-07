# main.py
# Sharkyo — main CLI entry point.

import sys

from sharkyo.agent import Agent
from sharkyo.cli import handle_flags, print_help
from sharkyo.constants import setup_dirs

# Flags that consume the next positional token as their value.
_FLAGS_WITH_VALUE = {"--add-key", "--provider", "--base-url", "--delete-knowledge"}


def _extract_user_input(args: list[str]) -> str:
    # Filter out all flags and their value tokens, joining the rest as the user prompt.
    parts: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _FLAGS_WITH_VALUE:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        parts.append(arg)
        i += 1
    return " ".join(parts).strip()


def main() -> None:
    # Parse CLI input and run Sharkyo.
    setup_dirs()

    args = sys.argv[1:]
    handle_flags(args)

    user_input = _extract_user_input(args)
    if not user_input:
        print_help()
        sys.exit(0)

    agent = Agent()
    agent.run(user_input)


if __name__ == "__main__":
    main()
