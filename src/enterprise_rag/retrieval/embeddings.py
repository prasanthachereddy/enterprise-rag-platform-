"""Embedding providers. Local (Docker) now; a Bedrock provider can implement the same protocol."""

import hashlib
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import requests


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    """Calls a Text Embeddings Inference server (the `embeddings` container)."""

    def __init__(
        self,
        url: str,
        model_name: str,
        dimensions: int,
        batch_size: int = 32,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._post = post or requests.post

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            payload = {"inputs": batch, "normalize": True, "truncate": True}
            response = self._post(f"{self.url}/embed", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            if len(data) != len(batch):
                raise ValueError("embedding server returned the wrong number of vectors")
            for vector in data:
                if len(vector) != self.dimensions:
                    raise ValueError(
                        f"expected {self.dimensions} dimensions but got {len(vector)}; "
                        "check LOCAL_EMBEDDING_DIMENSIONS and the model"
                    )
            vectors.extend(data)
        return vectors


class CachedEmbedder:
    """Stores vectors in a small SQLite file so unchanged text is never embedded twice."""

    def __init__(self, inner: Embedder, db_path: Path) -> None:
        self.inner = inner
        self.model_name = inner.model_name
        self.dimensions = inner.dimensions
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector TEXT)")

    def _key(self, text: str) -> str:
        raw = f"{self.model_name}|{self.dimensions}|{text}".encode()
        return hashlib.sha256(raw).hexdigest()

    def embed(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(text) for text in texts]
        found: dict[str, list[float]] = {}
        for key in set(keys):
            row = self._db.execute("SELECT vector FROM vectors WHERE key = ?", (key,)).fetchone()
            if row:
                found[key] = json.loads(row[0])
        missing = [(k, t) for k, t in dict(zip(keys, texts, strict=True)).items() if k not in found]
        if missing:
            new_vectors = self.inner.embed([text for _, text in missing])
            for (key, _), vector in zip(missing, new_vectors, strict=True):
                found[key] = vector
                self._db.execute(
                    "INSERT OR REPLACE INTO vectors VALUES (?, ?)", (key, json.dumps(vector))
                )
            self._db.commit()
        return [found[key] for key in keys]

    def close(self) -> None:
        self._db.close()