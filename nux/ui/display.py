# ui/display.py
# Rich-based display utilities and spinner for Nux.

import sys
from contextlib import nullcontext

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from yaspin import yaspin

console = Console(force_terminal=True)

QUESTIONARY_STYLE_SPEC = [
    ("qmark", "fg:#00bcd4 bold"),
    ("question", "bold"),
    ("pointer", "fg:#00bcd4 bold"),
    ("highlighted", "fg:#00bcd4 bold"),
    ("selected", "fg:#00bcd4"),
]

_SHINY = "dots"


def yaspin_if_tty(spinner: str = _SHINY):
    if sys.stdout.isatty():
        return yaspin(spinner, text="nux")
    return nullcontext()


def is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


_MARKDOWN_MARKERS = ("**", "##", "```", "- ", "* ", "> ", "~~", "__", "1. ")


def _looks_like_markdown(text: str) -> bool:
    return any(m in text for m in _MARKDOWN_MARKERS)


def print_reply(text: str) -> None:
    console.print("[bold cyan]nux[/bold cyan]")
    if _looks_like_markdown(text):
        console.print(Padding(Markdown(text), (0, 2, 0, 2)))
    else:
        console.print(Padding(text, (0, 2, 0, 2)))


def print_info(msg: str) -> None:
    console.print(f"[dim]🡒[/dim] {msg}")


def print_error(msg: str) -> None:
    console.print(f"[bold red]x[/bold red] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green] {msg}")
