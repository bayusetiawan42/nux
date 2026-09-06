"""Rich-based display utilities and spinner for Sharkyo."""

from rich.console import Console
from rich.markdown import Markdown
from yaspin import yaspin
from yaspin.core import Spinner

console = Console(force_terminal=True)

# ---------------------------------------------------------------------------
# Spinner — shining blue text animation
# ---------------------------------------------------------------------------
_BLUE = "\033[94m"   # bright blue
_DIM  = "\033[2;37m" # dim gray
_RST  = "\033[0m"

_word = "sharkyo"
_shiny_frames = []
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

def _looks_like_markdown(text: str) -> bool:
    """Heuristic: check for common markdown markers."""
    markers = ("**", "##", "```", "- ", "* ", "> ", "~~", "__", "[")
    return any(m in text for m in markers)


def print_reply(text: str) -> None:
    """Print the assistant reply with sharkyo prefix."""
    console.print("[bold cyan]sharkyo[/bold cyan]", end=" ")
    if _looks_like_markdown(text):
        console.print(Markdown(text))
    else:
        console.print(text)


def print_info(msg: str) -> None:
    console.print(f"[cyan]~[/cyan] {msg}")


def print_error(msg: str) -> None:
    console.print(f"[bold red]x[/bold red] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[cyan]✓[/cyan] {msg}")


def prompt_user(msg: str) -> str:
    return console.input(f"[bold cyan]?[/bold cyan] {msg}")
