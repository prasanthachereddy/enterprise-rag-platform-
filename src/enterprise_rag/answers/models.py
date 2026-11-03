"""The shapes returned by the answer step."""

from dataclasses import dataclass, field

from enterprise_rag.retrieval.models import SearchResult


@dataclass(frozen=True)
class Citation:
    number: int
    chunk_id: str
    source_filename: str
    heading: str
    snippet: str


@dataclass(frozen=True)
class Answer:
    question: str
    text: str
    found: bool
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[SearchResult] = field(default_factory=list)