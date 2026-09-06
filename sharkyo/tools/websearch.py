"""Web search + fetch tool — DuckDuckGo search with automatic page reading."""

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
_TIMEOUT = 10
_MAX_SEARCH_RESULTS = 5
_MAX_PAGE_CHARS = 5000
_MAX_SNIPPET_CHARS = 300

# Tags to strip entirely (no text extracted)
_DISCARD_TAGS = {
    "script", "style", "noscript", "head", "meta", "link",
    "header", "footer", "nav", "aside", "form", "button",
    "iframe", "svg", "img",
}

SCHEMA = {
    "type": "function",
    "function": {
        "name": "WEBSEARCH",
        "description": (
            "Search the web or fetch a specific page. "
            "If 'query' is a URL (starts with http:// or https://), fetches that page directly and returns clean text. "
            "If 'query' is keywords, searches DuckDuckGo and automatically reads the top result page plus search snippets. "
            "Use this for any question requiring current information, facts, news, or reading a webpage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A URL to fetch directly, or search keywords to look up on the web.",
                },
            },
            "required": ["query"],
        },
    },
}


@dataclass
class _SearchResult:
    title: str
    url: str
    snippet: str


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _fetch_html(url: str, timeout: int = _TIMEOUT) -> str:
    """Fetch raw HTML from a URL with automatic decompression and SSL fallback."""
    import gzip
    import ssl
    import zlib

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            ctx = ssl._create_unverified_context()
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        else:
            raise e

    with resp:
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type}")
        raw = resp.read()
        encoding = resp.headers.get("Content-Encoding", "").lower()
        if "gzip" in encoding:
            raw = gzip.decompress(raw)
        elif "deflate" in encoding:
            raw = zlib.decompress(raw)
        return raw.decode("utf-8", errors="replace")



def _extract_text(html: str) -> str:
    """Strip HTML and return clean readable text from page."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_DISCARD_TAGS):
        tag.decompose()

    # Prefer semantic main content areas
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

    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text or "(No readable content found on this page)"


def _ddg_search(query: str) -> list[_SearchResult]:
    """Search DuckDuckGo Lite and return parsed results."""
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
        html = resp.read().decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr")
    results: list[_SearchResult] = []
    i = 0

    while i < len(rows) and len(results) < _MAX_SEARCH_RESULTS:
        row = rows[i]
        tds = row.find_all("td")
        if len(tds) < 2:
            i += 1
            continue

        if not re.match(r"^\d+\.$", tds[0].get_text(strip=True)):
            i += 1
            continue

        title = tds[1].get_text(strip=True)
        if not title:
            i += 1
            continue

        snippet = ""
        if i + 1 < len(rows):
            snippet_cell = rows[i + 1].find("td", class_="result-snippet")
            if snippet_cell:
                snippet = snippet_cell.get_text(" ", strip=True)[:_MAX_SNIPPET_CHARS]

        url = ""
        if i + 2 < len(rows):
            url_tds = rows[i + 2].find_all("td")
            if len(url_tds) >= 2:
                raw = url_tds[1].get_text(strip=True)
                if raw:
                    url = raw if raw.startswith("http") else f"https://{raw}"

        if title and url:
            results.append(_SearchResult(title=title, url=url, snippet=snippet))
        i += 4

    return results


def execute(args: dict, config: Config | None = None) -> tuple[str, bool]:
    """Execute WEBSEARCH: fetch URL directly, or search DDG and fetch top result."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' parameter is required.", True

    # Case 1: Direct URL → fetch page immediately
    if _is_url(query):
        print_info(f"Fetching: [bold cyan]{query}[/bold cyan]")
        try:
            html = _fetch_html(query)
            text = _extract_text(html)
        except Exception as e:
            print_error(f"Fetch failed: {e}")
            return f"Failed to fetch {query}: {e}", True

        if len(text) > _MAX_PAGE_CHARS:
            text = text[:_MAX_PAGE_CHARS] + f"\n\n[Content truncated at {_MAX_PAGE_CHARS} chars]"
        return f"Page content from {query}:\n\n{text}", True

    # Case 2: Keywords → search DDG, fetch top result with 5x fallback + show snippets
    print_info(f"Searching: [bold cyan]{query}[/bold cyan]")
    try:
        results = _ddg_search(query)
    except Exception as e:
        print_error(f"Search failed: {e}")
        return f"Search failed: {e}", True

    if not results:
        return f"No results found for: {query}", True

    # 5x Try Fallback: iterate through top 5 results until one yields readable content
    successful_result = None
    fetched_text = ""

    candidates = results[:5]
    for idx, candidate in enumerate(candidates, 1):
        print_info(f"Reading [dim]({idx}/{len(candidates)})[/dim]: [bold cyan]{candidate.url}[/bold cyan]")
        try:
            html = _fetch_html(candidate.url, timeout=5)
            text = _extract_text(html)
            # Must have substantial content (not empty, not just an error page / placeholder)
            if text and text != "(No readable content found on this page)" and len(text.strip()) > 80:
                successful_result = candidate
                fetched_text = text
                break
            else:
                print_info(f"Result #{idx} had insufficient content, trying fallback...")
        except Exception as e:
            print_info(f"Result #{idx} fetch failed ({e}), trying fallback...")

    # If a page was successfully fetched:
    if successful_result:
        if len(fetched_text) > _MAX_PAGE_CHARS:
            fetched_text = fetched_text[:_MAX_PAGE_CHARS] + f"\n\n[Content truncated at {_MAX_PAGE_CHARS} chars]"

        output_parts = [
            f"=== Page Content: {successful_result.title} ===",
            f"URL: {successful_result.url}",
            "",
            fetched_text,
            "",
            "=== Other Search Results (Snippets) ===",
        ]
        for idx, r in enumerate(results, 1):
            if r.url == successful_result.url:
                continue
            output_parts.append(f"[{idx}] {r.title}")
            output_parts.append(f"    URL: {r.url}")
            if r.snippet:
                output_parts.append(f"    {r.snippet}")
            output_parts.append("")

        return "\n".join(output_parts).strip(), True

    # Fallback: if all top 5 candidates failed, return all DDG snippets
    output_parts = [
        f"Search: {query}",
        "Notice: Could not load full pages for the top 5 links (SPA, paywall, or blocked).",
        "Using search snippets:\n",
    ]
    for idx, r in enumerate(results, 1):
        output_parts.append(f"[{idx}] {r.title}")
        output_parts.append(f"    URL: {r.url}")
        if r.snippet:
            output_parts.append(f"    {r.snippet}")
        output_parts.append("")

    return "\n".join(output_parts).strip(), True
