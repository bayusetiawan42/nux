# search/__init__.py
# Search package: BM25 search engine for skill documents.

from sharkyo.search.bm25 import BM25Searcher, tokenize
from sharkyo.search.result import SearchResult


def search_skills(query: str, top_k: int = 1) -> SearchResult | None:
    from sharkyo.core.constants import SKILLS_DIR

    searcher = BM25Searcher(documents_dir=SKILLS_DIR)
    matches = searcher.search(query, top_k=top_k)

    if not matches:
        return None

    return matches[0]


__all__ = ["BM25Searcher", "SearchResult", "search_skills", "tokenize"]
