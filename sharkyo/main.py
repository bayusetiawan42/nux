# main.py
# Sharkyo — main CLI entry point.

from sharkyo.agent import Agent
from sharkyo.cli import main as run_cli
from sharkyo.constants import setup_dirs


def main() -> None:
    # Parse CLI input and run Sharkyo.
    setup_dirs()
    prompt = run_cli()
    Agent().run(prompt)


if __name__ == "__main__":
    main()
