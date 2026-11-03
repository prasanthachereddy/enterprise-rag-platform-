"""Decide which retrieved passages really contain what the question asks about."""

from enterprise_rag.retrieval.models import SearchResult
from enterprise_rag.retrieval.rerank import tokens


def coverage(query_words: set[str], result: SearchResult) -> float:
    """Share of the question's words that appear in the passage text or heading."""
    if not query_words:
        return 0.0
    available = set(tokens(result.text)) | set(tokens(result.heading))
    return len(query_words & available) / len(query_words)


def select_evidence(
    question: str, results: list[SearchResult], min_coverage: float
) -> list[SearchResult]:
    """Keep passages that cover enough of the question, best coverage first."""
    query_words = set(tokens(question))
    scored = [(coverage(query_words, result), result) for result in results]
    kept = [(score, result) for score, result in scored if score > 0 and score >= min_coverage]
    kept.sort(key=lambda pair: pair[0], reverse=True)  # stable: ties keep the search order
    return [result for _, result in kept]