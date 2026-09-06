"""Web search tool using DuckDuckGo Lite + BeautifulSoup."""

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from bs4 import BeautifulSoup

from sharkyo.config import Config
from sharkyo.display import print_error, print_info

_DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT = 8
_DEFAULT_MAX_RESULTS = 5
_MAX_SNIPPET_CHARS = 300

SCHEMA = {
    "type": "function",
    "function": {
        "name": "WEBSEARCH",
        "description": (
            "Search the web for information using DuckDuckGo. "
            "Returns a list of titles, URLs, and short snippets from search results. "
            "Use this when the user asks for current information, facts, news, or anything you are not sure about."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5, max: 10).",
                },
            },
            "required": ["query"],
        },
    },
}


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _fetch_ddg(query: str) -> str:
    """POST query to DuckDuckGo Lite and return raw HTML."""
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(
        _DDG_LITE_URL,
        data=data,
        headers={
            "User-Agent": _USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_results(html: str, max_results: int) -> list[SearchResult]:
    """Parse DuckDuckGo Lite HTML into SearchResult objects.

    DDG Lite structure (per result, 4 rows):
      Row 0: number cell | title cell (plain text)
      Row 1: empty       | snippet cell (class=result-snippet)
      Row 2: empty       | url cell (plain text, www.example.com/...)
      Row 3: empty       | empty (spacer)
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr")
    results: list[SearchResult] = []
    i = 0

    while i < len(rows) and len(results) < max_results:
        row = rows[i]
        tds = row.find_all("td")
        if len(tds) < 2:
            i += 1
            continue

        # First cell: row number like "1."
        first_text = tds[0].get_text(strip=True)
        if not re.match(r"^\d+\.$", first_text):
            i += 1
            continue

        title = tds[1].get_text(strip=True)
        if not title:
            i += 1
            continue

        # Row i+1: snippet
        snippet = ""
        if i + 1 < len(rows):
            snippet_row = rows[i + 1].find("td", class_="result-snippet")
            if snippet_row:
                snippet = snippet_row.get_text(" ", strip=True)[:_MAX_SNIPPET_CHARS]

        # Row i+2: url
        url = ""
        if i + 2 < len(rows):
            url_tds = rows[i + 2].find_all("td")
            if len(url_tds) >= 2:
                raw_url = url_tds[1].get_text(strip=True)
                if raw_url:
                    url = raw_url if raw_url.startswith("http") else f"https://{raw_url}"

        results.append(SearchResult(title=title, url=url, snippet=snippet))
        i += 4  # jump to next result block

    return results


def _format_for_model(results: list[SearchResult], query: str) -> str:
    """Format results as structured text for the model."""
    if not results:
        return f"No results found for: {query}"

    lines = [f"Web search results for: {query}\n"]
    for idx, r in enumerate(results, 1):
        lines.append(f"[{idx}] {r.title}")
        if r.url:
            lines.append(f"    URL: {r.url}")
        if r.snippet:
            lines.append(f"    {r.snippet}")
        lines.append("")

    return "\n".join(lines).strip()


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Execute a web search and return formatted results to the model."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' parameter is required.", True

    max_results = min(int(args.get("max_results", _DEFAULT_MAX_RESULTS)), 10)
    print_info(f"Searching: [bold cyan]{query}[/bold cyan]")

    try:
        html = _fetch_ddg(query)
        results = _parse_results(html, max_results)
    except Exception as e:
        print_error(f"Web search failed: {e}")
        return f"Web search failed: {e}", True

    output = _format_for_model(results, query)
    return output, True
