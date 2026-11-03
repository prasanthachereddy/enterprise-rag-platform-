"""The result shape returned by every retrieval mode."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    source_filename: str
    heading: str
    text: str
    score: float
    rank: int