"""BM25, vector, hybrid (Reciprocal Rank Fusion) and reranked search."""

from typing import Any, Literal

from enterprise_rag.retrieval.embeddings import Embedder
from enterprise_rag.retrieval.models import SearchResult
from enterprise_rag.retrieval.rerank import rerank

Mode = Literal["bm25", "vector", "hybrid", "rerank"]
SOURCE_FILTER = {"excludes": ["embedding"]}


def _to_results(response: dict[str, Any]) -> list[SearchResult]:
    results = []
    for rank, hit in enumerate(response["hits"]["hits"], start=1):
        source = hit["_source"]
        results.append(
            SearchResult(
                chunk_id=source["chunk_id"],
                document_id=source["document_id"],
                source_filename=source["source_filename"],
                heading=source.get("heading", ""),
                text=source["text"],
                score=float(hit["_score"] or 0.0),
                rank=rank,
            )
        )
    return results


def bm25_search(client: Any, index: str, query: str, top_k: int) -> list[SearchResult]:
    body = {
        "size": top_k,
        "_source": SOURCE_FILTER,
        "query": {"multi_match": {"query": query, "fields": ["text", "heading^2"]}},
    }
    return _to_results(client.search(index=index, body=body))


def vector_search(
    client: Any, index: str, embedder: Embedder, query: str, top_k: int
) -> list[SearchResult]:
    vector = embedder.embed([query])[0]
    body = {
        "size": top_k,
        "_source": SOURCE_FILTER,
        "query": {"knn": {"embedding": {"vector": vector, "k": top_k}}},
    }
    return _to_results(client.search(index=index, body=body))


def rrf_fuse(rankings: list[list[SearchResult]], k: int, top_k: int) -> list[SearchResult]:
    """Reciprocal Rank Fusion: each list adds 1 / (k + rank) to a chunk's score."""
    scores: dict[str, float] = {}
    by_id: dict[str, SearchResult] = {}
    for ranking in rankings:
        for position, result in enumerate(ranking, start=1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1 / (k + position)
            by_id.setdefault(result.chunk_id, result)
    ordered = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)[:top_k]
    return [
        SearchResult(
            chunk_id=by_id[cid].chunk_id,
            document_id=by_id[cid].document_id,
            source_filename=by_id[cid].source_filename,
            heading=by_id[cid].heading,
            text=by_id[cid].text,
            score=round(scores[cid], 6),
            rank=rank,
        )
        for rank, cid in enumerate(ordered, start=1)
    ]


def search(
    mode: Mode,
    client: Any,
    index: str,
    embedder: Embedder,
    query: str,
    top_k: int,
    candidates: int,
    rrf_k: int,
) -> list[SearchResult]:
    if mode == "bm25":
        return bm25_search(client, index, query, top_k)
    if mode == "vector":
        return vector_search(client, index, embedder, query, top_k)
    pool = max(candidates, top_k)
    fused = rrf_fuse(
        [
            bm25_search(client, index, query, pool),
            vector_search(client, index, embedder, query, pool),
        ],
        rrf_k,
        pool,
    )
    if mode == "hybrid":
        return fused[:top_k]
    return rerank(query, fused, top_k)