"""Run the golden set and write docs\\EVALUATION.md. Needs Docker; Bedrock only if asked."""

import argparse
from datetime import UTC, datetime

from enterprise_rag.answers.service import ask, create_bedrock_client
from enterprise_rag.config import get_settings, project_root
from enterprise_rag.evaluation.golden import load_golden
from enterprise_rag.evaluation.report import render_report
from enterprise_rag.evaluation.runner import (
    AnswerReport,
    RetrievalReport,
    evaluate_answers,
    evaluate_retrieval,
)
from enterprise_rag.retrieval.embeddings import LocalEmbedder
from enterprise_rag.retrieval.index import create_client
from enterprise_rag.retrieval.models import SearchResult
from enterprise_rag.retrieval.search import Mode, search

MODES: list[Mode] = ["bm25", "vector", "hybrid", "rerank"]
TOP_K = 5


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and answers")
    parser.add_argument("--index", default="enterprise-policy-eval")
    parser.add_argument("--answers", choices=["none", "offline", "bedrock", "both"], default="both")
    parser.add_argument("--golden", default="data/eval/golden.jsonl")
    parser.add_argument("--out", default="docs/EVALUATION.md")
    args = parser.parse_args()

    root = project_root()
    settings = get_settings().model_copy(update={"opensearch_index": args.index})
    questions = load_golden(root / args.golden)
    client = create_client(settings.opensearch_url)
    embedder = LocalEmbedder(
        settings.local_embedding_url,
        settings.local_embedding_model,
        settings.local_embedding_dimensions,
    )

    retrieval: list[RetrievalReport] = []
    for mode in MODES:
        def search_fn(query: str, mode: Mode = mode) -> list[SearchResult]:
            return search(
                mode, client, args.index, embedder, query, TOP_K,
                settings.retrieval_candidates, settings.rrf_k,
            )  # fmt: skip

        retrieval.append(evaluate_retrieval(mode, questions, search_fn))
        print(f"retrieval done: {mode}")

    answers: list[AnswerReport] = []
    if args.answers in ("offline", "both"):
        offline = settings.model_copy(update={"answer_mode": "offline"})
        answers.append(
            evaluate_answers(
                "offline", questions, lambda q: ask(q, offline, client, embedder, "rerank")
            )
        )
        print("answers done: offline")
    if args.answers in ("bedrock", "both"):
        live = settings.model_copy(update={"answer_mode": "bedrock"})
        llm = create_bedrock_client(live)
        answers.append(
            evaluate_answers(
                f"bedrock ({live.bedrock_chat_model_id})",
                questions,
                lambda q: ask(q, live, client, embedder, "rerank", llm=llm),
            )
        )
        print("answers done: bedrock")

    info = {
        "chunk_size": str(settings.chunk_size),
        "chunk_overlap": str(settings.chunk_overlap),
        "retrieval_top_k": str(TOP_K),
        "retrieval_candidates": str(settings.retrieval_candidates),
        "rrf_k": str(settings.rrf_k),
        "min_query_coverage": str(settings.min_query_coverage),
        "embedding_model": settings.local_embedding_model,
        "answer_model": settings.bedrock_chat_model_id,
    }
    documents = len(list((root / "data" / "sample_docs").glob("*"))) + len(
        list((root / "data" / "eval_docs").glob("*"))
    )
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    report = render_report(retrieval, answers, info, stamp, documents, args.golden)
    out.write_text(report, encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()