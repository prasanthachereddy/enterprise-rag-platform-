import pytest

from enterprise_rag.ingestion.chunking import chunk_sections
from enterprise_rag.ingestion.models import ExtractedSection

LONG = " ".join(
    f"Sentence number {i} explains policy detail {i * 7} for employees." for i in range(1, 40)
)


def run(text: str, size: int = 200, overlap: int = 30, heading: str = "H") -> list[str]:
    chunks = chunk_sections([ExtractedSection(heading, text)], "doc-1", "f.txt", size, overlap)
    return [c.text for c in chunks]


def test_chunks_fit_and_never_split_words() -> None:
    texts = run(LONG)
    source_words = set(LONG.split())
    assert len(texts) > 3
    for text in texts:
        assert len(text) <= 200
        assert set(text.split()) <= source_words


def test_short_paragraphs_stay_together() -> None:
    texts = run("First paragraph.\n\nSecond paragraph.", size=200)
    assert texts == ["First paragraph.\n\nSecond paragraph."]


def test_consecutive_chunks_overlap_on_whole_words() -> None:
    texts = run(LONG)
    shared = set(texts[0].split()[-3:]) & set(texts[1].split()[:8])
    assert shared


def test_huge_token_is_hard_split() -> None:
    texts = run("x" * 250, size=100, overlap=10)
    assert all(len(t) <= 100 for t in texts)
    assert "".join(texts) == "x" * 250


def test_headings_and_ids_are_kept() -> None:
    sections = [ExtractedSection("A", "One."), ExtractedSection("B", "Two.")]
    chunks = chunk_sections(sections, "doc-9", "f.txt", 100, 10)
    assert [c.heading for c in chunks] == ["A", "B"]
    assert [c.chunk_id for c in chunks] == ["doc-9-c0000", "doc-9-c0001"]
    assert chunks[1].chunk_index == 1


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError, match="smaller"):
        run("text", size=50, overlap=50)