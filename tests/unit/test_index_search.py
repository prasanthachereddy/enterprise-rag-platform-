from typing import Any

from enterprise_rag.ingestion.models import Chunk
from enterprise_rag.retrieval.index import build_actions, build_mapping, index_chunks
from enterprise_rag.retrieval.search import bm25_search, search, vector_search


def hit(chunk_id: str, text: str, heading: str = "H", score: float = 1.0) -> dict[str, Any]:
    source = {
        "chunk_id": chunk_id,
        "document_id": "doc-1",
        "source_filename": "f.txt",
        "heading": heading,
        "text": text,
    }
    return {"_score": score, "_source": source}


class FakeClient:
    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []

    def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        self.bodies.append(body)
        if "knn" in body["query"]:
            hits = [hit("c2", "vector best"), hit("c1", "both lists")]
        else:
            hits = [hit("c1", "both lists"), hit("c3", "bm25 only")]
        return {"hits": {"hits": hits}}


class FakeEmbedder:
    model_name = "fake"
    dimensions = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_mapping_uses_the_embedding_dimension() -> None:
    mapping = build_mapping(384)
    assert mapping["mappings"]["properties"]["embedding"]["dimension"] == 384
    assert mapping["settings"]["index"]["knn"] is True


def test_actions_use_chunk_id_so_reindexing_overwrites() -> None:
    chunk = Chunk("doc-1-c0000", "doc-1", "f.txt", "Head", 0, "Body")
    actions = build_actions("idx", [chunk], [[0.5, 0.5]])
    assert actions[0]["_id"] == "doc-1-c0000"
    assert actions[0]["_source"]["embedding"] == [0.5, 0.5]


def test_index_chunks_embeds_heading_and_text_then_bulk_loads() -> None:
    captured: dict[str, Any] = {}

    def fake_bulk(client: Any, actions: list[dict[str, Any]], **kwargs: Any) -> None:
        captured["actions"] = actions
        captured["kwargs"] = kwargs

    chunks = [Chunk("c0", "d", "f.txt", "Head", 0, "Body"), Chunk("c1", "d", "f.txt", "", 1, "T")]
    count = index_chunks(object(), "idx", chunks, FakeEmbedder(), bulk_fn=fake_bulk)
    assert count == 2
    assert len(captured["actions"]) == 2
    assert captured["kwargs"] == {"refresh": True}


def test_bm25_and_vector_requests_are_well_formed() -> None:
    client = FakeClient()
    bm25 = bm25_search(client, "idx", "leave days", 3)
    vector = vector_search(client, "idx", FakeEmbedder(), "leave days", 3)
    assert client.bodies[0]["query"]["multi_match"]["fields"] == ["text", "heading^2"]
    assert client.bodies[1]["query"]["knn"]["embedding"]["k"] == 3
    assert client.bodies[1]["_source"] == {"excludes": ["embedding"]}
    assert [r.chunk_id for r in bm25] == ["c1", "c3"]
    assert vector[0].rank == 1


def test_hybrid_puts_the_chunk_found_by_both_first_and_rerank_keeps_top_k() -> None:
    client = FakeClient()
    hybrid = search("hybrid", client, "idx", FakeEmbedder(), "both lists", 2, 10, 60)
    assert [r.chunk_id for r in hybrid][0] == "c1"
    assert len(hybrid) == 2
    reranked = search("rerank", client, "idx", FakeEmbedder(), "both lists", 1, 10, 60)
    assert len(reranked) == 1