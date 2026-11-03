from pathlib import Path
from typing import Any

import pytest

from enterprise_rag.retrieval.embeddings import CachedEmbedder, LocalEmbedder


class FakeResponse:
    def __init__(self, data: list[list[float]]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[list[float]]:
        return self._data


def make_post(dimensions: int, calls: list[dict[str, Any]]) -> Any:
    def post(url: str, json: dict[str, Any], timeout: int) -> FakeResponse:
        calls.append({"url": url, "json": json})
        return FakeResponse([[0.1] * dimensions for _ in json["inputs"]])

    return post


def test_local_embedder_batches_and_sends_expected_payload() -> None:
    calls: list[dict[str, Any]] = []
    embedder = LocalEmbedder("http://x:8080/", "m", 4, batch_size=2, post=make_post(4, calls))
    vectors = embedder.embed(["a", "b", "c"])
    assert len(vectors) == 3
    assert len(calls) == 2
    assert calls[0]["url"] == "http://x:8080/embed"
    assert calls[0]["json"] == {"inputs": ["a", "b"], "normalize": True, "truncate": True}


def test_local_embedder_rejects_wrong_dimensions() -> None:
    embedder = LocalEmbedder("http://x", "m", 8, post=make_post(4, []))
    with pytest.raises(ValueError, match="expected 8 dimensions"):
        embedder.embed(["a"])


def test_cached_embedder_only_embeds_new_text(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    inner = LocalEmbedder("http://x", "m", 4, post=make_post(4, calls))
    cached = CachedEmbedder(inner, tmp_path / "cache.sqlite")
    first = cached.embed(["a", "b"])
    second = cached.embed(["b", "a", "c"])
    cached.close()
    assert len(calls) == 2
    assert calls[1]["json"]["inputs"] == ["c"]
    assert second[0] == first[1]
    assert len(second) == 3


def test_cache_survives_a_new_instance(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    inner = LocalEmbedder("http://x", "m", 4, post=make_post(4, calls))
    first = CachedEmbedder(inner, tmp_path / "cache.sqlite")
    first.embed(["same"])
    first.close()
    second = CachedEmbedder(inner, tmp_path / "cache.sqlite")
    second.embed(["same"])
    second.close()
    assert len(calls) == 1