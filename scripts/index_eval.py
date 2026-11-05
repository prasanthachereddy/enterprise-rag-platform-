"""Index the evaluation corpus (sample_docs + eval_docs) into a separate OpenSearch index."""

import argparse

from enterprise_rag.config import get_settings, project_root
from enterprise_rag.ingestion.registry import Registry
from enterprise_rag.ingestion.service import ingest_file
from enterprise_rag.retrieval.embeddings import CachedEmbedder, LocalEmbedder
from enterprise_rag.retrieval.index import create_client, index_chunks, recreate_index

DEFAULT_INDEX = "enterprise-policy-eval"


def main() -> None:
    parser = argparse.ArgumentParser(description="Index the evaluation corpus")
    parser.add_argument("--index", default=DEFAULT_INDEX)
    args = parser.parse_args()
    root = project_root()
    settings = get_settings()
    out_dir = root / "data" / "processed"
    registry = Registry(out_dir / "eval_registry.json")
    chunks = []
    documents = 0
    for folder in ("sample_docs", "eval_docs"):
        for path in sorted((root / "data" / folder).glob("*")):
            if path.is_file():
                chunks.extend(ingest_file(path, settings, registry).chunks)
                documents += 1
    embedder = CachedEmbedder(
        LocalEmbedder(
            settings.local_embedding_url,
            settings.local_embedding_model,
            settings.local_embedding_dimensions,
        ),
        out_dir / "embedding_cache.sqlite",
    )
    client = create_client(settings.opensearch_url)
    recreate_index(client, args.index, embedder.dimensions)
    count = index_chunks(client, args.index, chunks, embedder)
    embedder.close()
    print(f"Indexed {count} chunks from {documents} documents into '{args.index}'")


if __name__ == "__main__":
    main()