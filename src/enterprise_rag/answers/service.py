"""Question in, safe answer out: search, check the evidence, then answer or refuse."""

import logging
from typing import Any

from enterprise_rag.answers.bedrock import generate_answer
from enterprise_rag.answers.evidence import select_evidence
from enterprise_rag.answers.models import Answer
from enterprise_rag.answers.offline import NOT_FOUND_TEXT, build_offline_answer
from enterprise_rag.config import Settings
from enterprise_rag.observability.logging_config import log_event
from enterprise_rag.retrieval.embeddings import Embedder
from enterprise_rag.retrieval.search import Mode, search

LOGGER = logging.getLogger(__name__)
MAX_QUESTION_CHARS = 500


def create_bedrock_client(settings: Settings) -> Any:
    import boto3

    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def ask(
    question: str,
    settings: Settings,
    client: Any,
    embedder: Embedder,
    mode: Mode = "rerank",
    llm: Any | None = None,
) -> Answer:
    clean = " ".join(question.split())
    if not clean:
        raise ValueError("question is empty")
    if len(clean) > MAX_QUESTION_CHARS:
        raise ValueError(f"question is longer than {MAX_QUESTION_CHARS} characters")
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
    if settings.answer_mode == "bedrock":
        evidence = select_evidence(clean, results, settings.min_query_coverage)
        if evidence:  # no evidence means no model call and no cost
            answer = generate_answer(
                llm or create_bedrock_client(settings),
                settings.bedrock_chat_model_id,
                settings.answer_max_tokens,
                clean,
                evidence,
                results,
            )
        else:
            answer = Answer(question=clean, text=NOT_FOUND_TEXT, found=False, retrieved=results)
    else:
        answer = build_offline_answer(clean, results, settings.min_query_coverage)
    log_event(
        LOGGER,
        logging.INFO,
        "question_answered",
        answer_mode=settings.answer_mode,
        mode=mode,
        found=answer.found,
        result_count=len(results),
        citation_count=len(answer.citations),
    )
    return answer