"""Ask a question. Example: python scripts\\ask.py "how many days of annual leave" """

import argparse

from enterprise_rag.answers.service import ask
from enterprise_rag.config import get_settings
from enterprise_rag.retrieval.embeddings import LocalEmbedder
from enterprise_rag.retrieval.index import create_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the policy assistant a question")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["bm25", "vector", "hybrid", "rerank"], default="rerank")
    args = parser.parse_args()
    settings = get_settings()
    embedder = LocalEmbedder(
        settings.local_embedding_url,
        settings.local_embedding_model,
        settings.local_embedding_dimensions,
    )
    client = create_client(settings.opensearch_url)
    answer = ask(args.question, settings, client, embedder, args.mode)
    print(answer.text)
    for citation in answer.citations:
        print(f"  [{citation.number}] {citation.source_filename} | {citation.heading or '-'}")


if __name__ == "__main__":
    main()