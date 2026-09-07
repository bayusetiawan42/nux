# display.py
# Rich-based display utilities and spinner for Sharkyo.

import sys
from contextlib import nullcontext

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from yaspin import yaspin

console = Console()

# Questionary color theme shared by the CMD confirm and QUESTIONARY tool.
QUESTIONARY_STYLE_SPEC = [
    ("qmark",       "fg:#00bcd4 bold"),
    ("question",    "bold"),
    ("pointer",     "fg:#00bcd4 bold"),
    ("highlighted", "fg:#00bcd4 bold"),
    ("selected",    "fg:#00bcd4"),
]

# ---------------------------------------------------------------------------
# Spinner — animated "thinking" indicator shown while the model responds.
# Uses yaspin's built-in frames: custom ANSI-colored frames inflate the
# len()/width math and crash even on real terminals ("too small").
# ---------------------------------------------------------------------------
_SHINY = "dots"


def yaspin_if_tty(spinner: str = _SHINY):
    # yaspin raises a ValueError when stdout is not a real terminal (pipes,
    # redirection, CI) or when custom frames overflow the terminal width.
    # Render only on real interactive TTYs using built-in safe frames.
    if sys.stdout.isatty():
        return yaspin(spinner, text="sharkyo")
    return nullcontext()


def is_interactive() -> bool:
    # True only when both stdin and stdout are real terminals, so interactive
    # prompts (questionary/prompt_toolkit) can actually be displayed.
    return sys.stdin.isatty() and sys.stdout.isatty()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
_MARKDOWN_MARKERS = ("**", "##", "```", "- ", "* ", "> ", "~~", "__", "1. ")


def _looks_like_markdown(text: str) -> bool:
    # Heuristic check for common markdown markers.
    return any(m in text for m in _MARKDOWN_MARKERS)


def print_reply(text: str) -> None:
    # Print the assistant reply with sharkyo prefix.
    # Renders as Markdown if markdown markers are detected.
    if _looks_like_markdown(text):
        console.print("[bold cyan]sharkyo[/bold cyan]")
        console.print(Padding(Markdown(text), (0, 0, 0, 2)))
    else:
        console.print(f"[bold cyan]sharkyo[/bold cyan] {text}")


def print_info(msg: str) -> None:
    # Print an informational notice.
    console.print(f"  [cyan]~[/cyan] {msg}")


def print_error(msg: str) -> None:
    # Print an error message.
    console.print(f"  [bold red]x[/bold red] {msg}")


def print_success(msg: str) -> None:
    # Print a success message.
    console.print(f"  [cyan]✓[/cyan] {msg}")
