"""A simple, explainable local reranker. Replace it with a cross-encoder later."""

import re
from dataclasses import replace

from enterprise_rag.retrieval.models import SearchResult

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "many", "much", "of", "on", "or", "the", "to", "what",
    "when", "which", "who", "with",
}  # fmt: skip


def tokens(text: str) -> list[str]:
    """Lower-case words without stopwords; a trailing plural 's' is removed."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if w not in STOPWORDS]


def _bigrams(words: list[str]) -> set[tuple[str, str]]:
    return set(zip(words, words[1:], strict=False))


def rerank(query: str, results: list[SearchResult], top_k: int) -> list[SearchResult]:
    """Re-order candidates by word coverage, phrase match, heading match and original rank."""
    query_words = tokens(query)
    if not query_words or not results:
        return results[:top_k]
    query_set = set(query_words)
    query_pairs = _bigrams(query_words)
    scored: list[tuple[float, SearchResult]] = []
    for position, result in enumerate(results):
        body_words = tokens(result.text)
        heading_words = set(tokens(result.heading))
        coverage = len(query_set & (set(body_words) | heading_words)) / len(query_set)
        phrase = len(query_pairs & _bigrams(body_words)) / len(query_pairs) if query_pairs else 0.0
        heading = len(query_set & heading_words) / len(query_set)
        prior = 1 / (1 + position)
        score = 0.4 * coverage + 0.2 * phrase + 0.1 * heading + 0.3 * prior
        scored.append((score, result))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        replace(result, score=round(score, 4), rank=rank)
        for rank, (score, result) in enumerate(scored[:top_k], start=1)
    ]