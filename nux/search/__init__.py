# search/__init__.py
# Search package: BM25 search engine for skill documents.

from nux.search.bm25 import BM25Searcher, tokenize
from nux.search.result import SearchResult


def search_skills(query: str, top_k: int = 1) -> SearchResult | None:
    from nux.core.constants import SKILLS_DIR

    searcher = BM25Searcher(documents_dir=SKILLS_DIR)
    matches = searcher.search(query, top_k=top_k)

    if not matches:
        return None

    return matches[0]


__all__ = ["BM25Searcher", "SearchResult", "search_skills", "tokenize"]
