"""Lightweight BM25 search engine for internal skills."""

from dataclasses import dataclass
import math
import os
import re
from pathlib import Path

from sharkyo.constants import SKILLS_DIR


@dataclass
class SearchResult:
    """Represents a matched skill document."""
    name: str
    title: str
    content: str
    score: float


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\b\w+\b", text.lower())


class BM25Searcher:
    """In-memory BM25 ranker for skills."""

    def __init__(self, skills_dir: str | None = None, k1: float = 1.5, b: float = 0.75) -> None:
        self.skills_dir = Path(skills_dir or SKILLS_DIR)
        self.k1 = k1
        self.b = b

    def _extract_title(self, content: str, default: str) -> str:
        """Extract first Markdown header or fallback to filename."""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return default

    def search(self, query: str, top_k: int = 3, min_score: float = 0.1) -> list[SearchResult]:
        """Search skill documents using BM25 ranking."""
        query_tokens = _tokenize(query)
        if not query_tokens or not self.skills_dir.exists():
            return []

        # Load all documents
        docs: list[dict] = []
        doc_lengths: list[int] = []
        doc_freqs: dict[str, int] = {}

        for file_path in sorted(self.skills_dir.glob("*.md")):
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            stem = file_path.stem
            title = self._extract_title(content, stem)
            tokens = _tokenize(f"{title} {title} {content}")  # Give title double weight
            doc_len = len(tokens)
            if doc_len == 0:
                continue

            # Term frequencies for this document
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for t in tf.keys():
                doc_freqs[t] = doc_freqs.get(t, 0) + 1

            docs.append({
                "name": stem,
                "title": title,
                "content": content,
                "tf": tf,
                "len": doc_len,
            })
            doc_lengths.append(doc_len)

        n_docs = len(docs)
        if n_docs == 0:
            return []

        avg_doc_len = sum(doc_lengths) / n_docs

        # Calculate BM25 scores
        results: list[SearchResult] = []
        for doc in docs:
            score = 0.0
            for qt in query_tokens:
                if qt not in doc["tf"]:
                    continue
                df = doc_freqs.get(qt, 0)
                # BM25 IDF formula with +1 smoothing
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                f = doc["tf"][qt]
                numerator = f * (self.k1 + 1.0)
                denominator = f + self.k1 * (1.0 - self.b + self.b * (doc["len"] / avg_doc_len))
                score += idf * (numerator / denominator)

            if score >= min_score:
                results.append(SearchResult(
                    name=doc["name"],
                    title=doc["title"],
                    content=doc["content"],
                    score=round(score, 3),
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


def search_skills(query: str, top_k: int = 1) -> str | None:
    """Convenience function: search skills and return formatted guide, or None."""
    searcher = BM25Searcher()
    matches = searcher.search(query, top_k=top_k)
    if not matches:
        return None

    top = matches[0]
    return f"### Skill Guide: {top.title} ({top.name})\n\n{top.content.strip()}"
