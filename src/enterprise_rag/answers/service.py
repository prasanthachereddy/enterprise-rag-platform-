"""Question in, safe answer out: search, check the evidence, then answer or refuse."""

import logging
from typing import Any

from enterprise_rag.answers.models import Answer
from enterprise_rag.answers.offline import build_offline_answer
from enterprise_rag.config import Settings
from enterprise_rag.observability.logging_config import log_event
from enterprise_rag.retrieval.embeddings import Embedder
from enterprise_rag.retrieval.search import Mode, search

LOGGER = logging.getLogger(__name__)
MAX_QUESTION_CHARS = 500


def ask(
    question: str,
    settings: Settings,
    client: Any,
    embedder: Embedder,
    mode: Mode = "rerank",
) -> Answer:
    clean = " ".join(question.split())
    if not clean:
        raise ValueError("question is empty")
    if len(clean) > MAX_QUESTION_CHARS:
        raise ValueError(f"question is longer than {MAX_QUESTION_CHARS} characters")
    if settings.answer_mode != "offline":
        raise NotImplementedError("only ANSWER_MODE=offline is available until Bedrock is added")
    results = search(
        mode,
        client,
        settings.opensearch_index,
        embedder,
        clean,
        settings.retrieval_top_k,
        settings.retrieval_candidates,
        settings.rrf_k,
    )
    answer = build_offline_answer(clean, results, settings.min_query_coverage)
    log_event(
        LOGGER,
        logging.INFO,
        "question_answered",
        mode=mode,
        found=answer.found,
        result_count=len(results),
        citation_count=len(answer.citations),
    )
    return answer