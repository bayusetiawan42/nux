"""Web page fetcher tool — fetches a URL and extracts clean readable text using BeautifulSoup."""

import urllib.request
from bs4 import BeautifulSoup

from sharkyo.config import Config
from sharkyo.display import print_error, print_info

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT = 10
_DEFAULT_MAX_CHARS = 6000

# Tags to completely discard (not even their text content)
_DISCARD_TAGS = {
    "script", "style", "noscript", "head", "meta", "link",
    "header", "footer", "nav", "aside", "form", "button",
    "iframe", "svg", "img",
}

SCHEMA = {
    "type": "function",
    "function": {
        "name": "WEBFETCH",
        "description": (
            "Fetch a specific web page URL and extract its clean readable text content. "
            "Use this after WEBSEARCH to read the actual content of a promising result URL. "
            "Returns plain text stripped of all HTML, CSS, and scripts. "
            "Do NOT use CMD with curl to read web pages — use this tool instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to fetch and read.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": f"Maximum characters of text to return (default: {_DEFAULT_MAX_CHARS}).",
                },
            },
            "required": ["url"],
        },
    },
}


def _extract_text(html: str, max_chars: int) -> str:
    """Strip HTML and return clean readable text from page content."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise tags entirely
    for tag in soup.find_all(_DISCARD_TAGS):
        tag.decompose()

    # Try to isolate main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main")
        or soup.find(class_="content")
        or soup.find(class_="article")
        or soup.body
        or soup
    )

    # Extract text with newlines preserved at block-level elements
    lines = []
    for elem in main.descendants:
        if not hasattr(elem, "name"):
            # It's a NavigableString (text node)
            text = elem.strip()
            if text:
                lines.append(text)
        elif elem.name in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "dt", "dd", "blockquote"}:
            lines.append("")  # insert blank line before block-level elements

    # Join and clean up excessive blank lines
    text = "\n".join(lines)
    import re
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[Page content truncated at {max_chars} chars]"

    return text or "(Page has no readable text content)"


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Fetch a URL and return clean extracted text to the model."""
    url = args.get("url", "").strip()
    if not url:
        return "Error: 'url' parameter is required.", True

    max_chars = min(int(args.get("max_chars", _DEFAULT_MAX_CHARS)), 12000)
    print_info(f"Fetching: [bold cyan]{url}[/bold cyan]")

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            # Only process HTML pages
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return f"Cannot read this URL (content type: {content_type})", True
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print_error(f"Fetch failed: {e}")
        return f"Failed to fetch URL: {e}", True

    text = _extract_text(html, max_chars)
    return f"Content from {url}:\n\n{text}", True
