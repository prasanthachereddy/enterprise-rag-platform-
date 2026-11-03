"""Offline answers: quote the best sentences of the best passage. No model call, no cost."""

import re

from enterprise_rag.answers.evidence import select_evidence
from enterprise_rag.answers.models import Answer, Citation
from enterprise_rag.retrieval.models import SearchResult
from enterprise_rag.retrieval.rerank import tokens

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
NOT_FOUND_TEXT = "I could not find an answer to this in the policy documents."
MAX_SENTENCES = 2
SNIPPET_CHARS = 200


def best_sentences(question: str, text: str, limit: int = MAX_SENTENCES) -> list[str]:
    """Return up to `limit` sentences that share the most words with the question."""
    query_words = set(tokens(question))
    flat = " ".join(text.split())
    sentences = [part.strip() for part in SENTENCE_SPLIT.split(flat) if part.strip()]
    scored = [(len(query_words & set(tokens(s))), index, s) for index, s in enumerate(sentences)]
    top = sorted((item for item in scored if item[0] > 0), key=lambda i: (-i[0], i[1]))[:limit]
    return [sentence for _, _, sentence in sorted(top, key=lambda item: item[1])]


def build_offline_answer(
    question: str, results: list[SearchResult], min_coverage: float
) -> Answer:
    """Answer from the best passage, or refuse safely when no passage covers the question."""
    evidence = select_evidence(question, results, min_coverage)
    if not evidence:
        return Answer(question=question, text=NOT_FOUND_TEXT, found=False, retrieved=results)
    best = evidence[0]
    flat = " ".join(best.text.split())
    sentences = best_sentences(question, best.text) or [flat[:300]]
    citation = Citation(
        number=1,
        chunk_id=best.chunk_id,
        source_filename=best.source_filename,
        heading=best.heading,
        snippet=flat[:SNIPPET_CHARS],
    )
    return Answer(
        question=question,
        text=" ".join(sentences) + " [1]",
        found=True,
        citations=[citation],
        retrieved=results,
    )