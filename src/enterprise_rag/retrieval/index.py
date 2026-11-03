"""Create the OpenSearch index and load chunks with their vectors."""

from collections.abc import Callable
from typing import Any

from opensearchpy import OpenSearch, helpers

from enterprise_rag.ingestion.models import Chunk
from enterprise_rag.retrieval.embeddings import Embedder


def build_mapping(dimensions: int) -> dict[str, Any]:
    return {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "source_filename": {"type": "keyword"},
                "heading": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimensions,
                    "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "lucene"},
                },
            }
        },
    }


def create_client(url: str) -> OpenSearch:
    return OpenSearch(hosts=[url], timeout=30)


def recreate_index(client: Any, index: str, dimensions: int) -> None:
    """Delete the index if it exists, then create it fresh (safe to repeat)."""
    if client.indices.exists(index=index):
        client.indices.delete(index=index)
    client.indices.create(index=index, body=build_mapping(dimensions))


def embedding_text(chunk: Chunk) -> str:
    return f"{chunk.heading}\n{chunk.text}" if chunk.heading else chunk.text


def build_actions(
    index: str, chunks: list[Chunk], vectors: list[list[float]]
) -> list[dict[str, Any]]:
    actions = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        document = chunk.to_dict()
        document["embedding"] = vector
        actions.append({"_index": index, "_id": chunk.chunk_id, "_source": document})
    return actions


def index_chunks(
    client: Any,
    index: str,
    chunks: list[Chunk],
    embedder: Embedder,
    bulk_fn: Callable[..., Any] = helpers.bulk,
) -> int:
    """Embed and index the chunks. Returns how many were indexed."""
    vectors = embedder.embed([embedding_text(chunk) for chunk in chunks])
    actions = build_actions(index, chunks, vectors)
    bulk_fn(client, actions, refresh=True)
    return len(actions)