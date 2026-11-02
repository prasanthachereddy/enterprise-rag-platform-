"""Data shapes shared by the ingestion steps."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractedSection:
    heading: str
    text: str


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    filename: str
    extension: str
    size_bytes: int
    sha256: str
    created_at: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    source_filename: str
    heading: str
    chunk_index: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)