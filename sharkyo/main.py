"""Sharkyo — main CLI entry point."""

import sys

from sharkyo.agent import Agent
from sharkyo.cli import handle_flags, print_help


def main() -> None:
    """Parse CLI input and run Sharkyo."""
    args = sys.argv[1:]
    handle_flags(args)

    # Filter out flags to assemble user prompt text
    flag_with_value = {"--add-key", "--provider", "--base-url", "--delete-knowledge"}
    user_parts = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in flag_with_value:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        user_parts.append(arg)
        i += 1

    user_input = " ".join(user_parts).strip()
    if not user_input:
        print_help()
        sys.exit(0)

    agent = Agent()
    agent.run(user_input)


if __name__ == "__main__":
    main()
