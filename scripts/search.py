"""Search the index. Example: python scripts\\search.py "how many leave days" --mode hybrid"""

import argparse

from enterprise_rag.config import get_settings
from enterprise_rag.retrieval.embeddings import LocalEmbedder
from enterprise_rag.retrieval.index import create_client
from enterprise_rag.retrieval.search import search


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the policy index")
    parser.add_argument("query")
    parser.add_argument("--mode", choices=["bm25", "vector", "hybrid", "rerank"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()
    settings = get_settings()
    embedder = LocalEmbedder(
        settings.local_embedding_url,
        settings.local_embedding_model,
        settings.local_embedding_dimensions,
    )
    results = search(
        args.mode,
        create_client(settings.opensearch_url),
        settings.opensearch_index,
        embedder,
        args.query,
        args.top_k or settings.retrieval_top_k,
        settings.retrieval_candidates,
        settings.rrf_k,
    )
    for result in results:
        snippet = " ".join(result.text.split())[:110]
        heading = result.heading or "-"
        print(f"{result.rank}. [{result.score:.4f}] {result.source_filename} | {heading}")
        print(f"   {snippet}")


if __name__ == "__main__":
    main()