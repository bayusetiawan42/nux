# display.py
# Rich-based display utilities and spinner for Sharkyo.

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from yaspin.core import Spinner

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
# Spinner — shining blue text animation
# ---------------------------------------------------------------------------
_BLUE = "\033[94m"   # bright blue
_DIM  = "\033[2;37m" # dim gray
_RST  = "\033[0m"

_word = "sharkyo"
_shiny_frames: list[str] = []
for _i in range(len(_word)):
    _frame = ""
    for _j, _ch in enumerate(_word):
        if _j == _i:
            _frame += f"{_BLUE}{_ch}{_RST}"
        else:
            _frame += f"{_DIM}{_ch}{_RST}"
    _frame += f"{_DIM}...{_RST}"
    _shiny_frames.append(_frame)

SHARK_SPINNER = Spinner(_shiny_frames, interval=100)


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
