"""Ingest the sample documents, embed the chunks, and load them into OpenSearch."""

from enterprise_rag.config import get_settings, project_root
from enterprise_rag.ingestion.registry import Registry
from enterprise_rag.ingestion.service import ingest_file
from enterprise_rag.retrieval.embeddings import CachedEmbedder, LocalEmbedder
from enterprise_rag.retrieval.index import create_client, index_chunks, recreate_index


def main() -> None:
    root = project_root()
    settings = get_settings()
    out_dir = root / "data" / "processed"
    registry = Registry(out_dir / "registry.json")
    chunks = []
    for path in sorted((root / "data" / "sample_docs").glob("*")):
        if path.is_file():
            chunks.extend(ingest_file(path, settings, registry).chunks)
    embedder = CachedEmbedder(
        LocalEmbedder(
            settings.local_embedding_url,
            settings.local_embedding_model,
            settings.local_embedding_dimensions,
        ),
        out_dir / "embedding_cache.sqlite",
    )
    client = create_client(settings.opensearch_url)
    recreate_index(client, settings.opensearch_index, embedder.dimensions)
    count = index_chunks(client, settings.opensearch_index, chunks, embedder)
    embedder.close()
    print(f"Indexed {count} chunks into '{settings.opensearch_index}'")


if __name__ == "__main__":
    main()