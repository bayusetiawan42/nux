# search/bm25.py
# Portable BM25 search engine. No Sharkyo-specific dependencies.

import math
import re
from pathlib import Path

from sharkyo.search.result import SearchResult


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class BM25Searcher:

    def __init__(
        self,
        documents_dir: str | Path | None = None,
        k1: float = 1.5,
        b: float = 0.75,
        glob_pattern: str = "*.md",
    ) -> None:
        self.documents_dir = Path(documents_dir) if documents_dir else None
        self.k1 = k1
        self.b = b
        self.glob_pattern = glob_pattern

    def _extract_title(self, content: str, default: str) -> str:
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return default

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.1,
    ) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents_dir or not self.documents_dir.exists():
            return []

        docs: list[dict] = []
        doc_lengths: list[int] = []
        doc_freqs: dict[str, int] = {}

        for file_path in sorted(self.documents_dir.glob(self.glob_pattern)):
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            stem = file_path.stem
            title = self._extract_title(content, stem)
            tokens = tokenize(f"{title} {title} {content}")
            doc_len = len(tokens)
            if doc_len == 0:
                continue

            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for t in tf:
                doc_freqs[t] = doc_freqs.get(t, 0) + 1

            docs.append(
                {
                    "name": stem,
                    "title": title,
                    "content": content,
                    "tf": tf,
                    "len": doc_len,
                }
            )
            doc_lengths.append(doc_len)

        n_docs = len(docs)
        if n_docs == 0:
            return []

        avg_doc_len = sum(doc_lengths) / n_docs

        results: list[SearchResult] = []
        for doc in docs:
            score = 0.0
            for qt in query_tokens:
                if qt not in doc["tf"]:
                    continue
                df = doc_freqs.get(qt, 0)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                f = doc["tf"][qt]
                numerator = f * (self.k1 + 1.0)
                denominator = f + self.k1 * (1.0 - self.b + self.b * (doc["len"] / avg_doc_len))
                score += idf * (numerator / denominator)

            if score >= min_score:
                results.append(
                    SearchResult(
                        name=doc["name"],
                        title=doc["title"],
                        content=doc["content"],
                        score=round(score, 3),
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
