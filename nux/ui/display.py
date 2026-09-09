# ui/display.py
# Rich-based display utilities and spinner for Nux.

import difflib
import os
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


def set_no_color() -> None:
    global console
    console = Console(force_terminal=True, no_color=True)


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


def unified_diff(old_content: str, new_content: str, path: str) -> list[str]:
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    return list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{os.path.basename(path)}",
            tofile=f"b/{os.path.basename(path)}",
        )
    )


def show_diff(old_content: str, new_content: str, path: str) -> None:
    diff = unified_diff(old_content, new_content, path)
    if not diff:
        console.print("[dim]No changes detected.[/dim]")
        return
    code = "".join(diff)
    console.print(Padding(Markdown(f"```diff\n{code}```"), (0, 2, 0, 2)))


def show_file_preview(content: str, path: str, max_lines: int = 40) -> None:
    lines = content.splitlines()
    console.print(f"[bold]New file: {os.path.basename(path)}[/bold]")
    preview = lines[:max_lines]
    for line in preview:
        console.print(f"  [green]+[/green] {line}")
    if len(lines) > max_lines:
        console.print(f"  [dim]... {len(lines) - max_lines} more lines[/dim]")
