"""Paragraph-aware chunking that never cuts a word (except one longer than a whole chunk)."""

import re

from enterprise_rag.ingestion.models import Chunk, ExtractedSection

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_words(text: str, size: int) -> list[str]:
    """Group words into parts of at most size characters."""
    parts: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > size:  # a huge token such as a long URL
            if current:
                parts.append(current)
                current = ""
            parts.append(word[:size])
            word = word[size:]
        candidate = f"{current} {word}".strip()
        if len(candidate) <= size:
            current = candidate
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts


def _pieces(paragraph: str, size: int) -> list[str]:
    """Split a paragraph at sentence ends, and at word gaps only if a sentence is too long."""
    if len(paragraph) <= size:
        return [paragraph]
    pieces: list[str] = []
    for sentence in SENTENCE_SPLIT.split(paragraph):
        if len(sentence) <= size:
            pieces.append(sentence)
        else:
            pieces.extend(_split_words(sentence, size))
    return pieces


def _tail_overlap(text: str, overlap: int) -> str:
    """Return roughly the last `overlap` characters, starting on a whole word."""
    if overlap <= 0 or len(text) <= overlap:
        return ""
    tail = text[-overlap:]
    if not text[-overlap - 1].isspace():
        words = tail.split(None, 1)
        tail = words[1] if len(words) == 2 else ""
    return " ".join(tail.split())


def _pack(text: str, size: int, overlap: int) -> list[str]:
    paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", text)]
    pieces: list[tuple[int, str]] = []
    for index, paragraph in enumerate(p for p in paragraphs if p):
        pieces.extend((index, piece) for piece in _pieces(paragraph, size))

    packed: list[str] = []
    current = ""
    last_index = -1
    for index, piece in pieces:
        separator = "" if not current else (" " if index == last_index else "\n\n")
        if current and len(current) + len(separator) + len(piece) > size:
            packed.append(current)
            tail = _tail_overlap(current, overlap)
            current = tail if tail and len(tail) + 1 + len(piece) <= size else ""
            separator = " " if current else ""
        current = f"{current}{separator}{piece}"
        last_index = index
    if current:
        packed.append(current)
    return packed


def chunk_sections(
    sections: list[ExtractedSection],
    document_id: str,
    source_filename: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Chunk each section separately so a chunk never mixes two headings."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    chunks: list[Chunk] = []
    for section in sections:
        for text in _pack(section.text, chunk_size, chunk_overlap):
            index = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}-c{index:04d}",
                    document_id=document_id,
                    source_filename=source_filename,
                    heading=section.heading,
                    chunk_index=index,
                    text=text,
                )
            )
    return chunks