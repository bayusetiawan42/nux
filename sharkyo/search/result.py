# search/result.py
# Search result dataclass.

from dataclasses import dataclass


@dataclass
class SearchResult:
    name: str
    title: str
    content: str
    score: float
