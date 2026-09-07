# tests/test_search.py
# Skill search tests.

from sharkyo.constants import SKILLS_DIR
from sharkyo.search import BM25Searcher, search_skills


def test_finds_relevant_skill():
    results = BM25Searcher(SKILLS_DIR).search("crontab schedule job", top_k=1)
    assert results and results[0].name == "crontab"


def test_no_match_returns_empty():
    results = BM25Searcher(SKILLS_DIR).search("zzqqxxyy nugget", top_k=3)
    assert results == []


def test_search_skills_formats_guide():
    guide = search_skills("network tools", top_k=1)
    assert guide is not None
    assert "### Skill Guide:" in guide

    assert search_skills("zzqqxxyy nugget") is None