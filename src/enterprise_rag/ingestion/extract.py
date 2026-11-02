"""Turn an uploaded file into sections: a heading plus the text under it."""

import re
from pathlib import PurePosixPath

from bs4 import BeautifulSoup, Tag

from enterprise_rag.ingestion.models import ExtractedSection

HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
BLOCK_TAGS = ["p", "li", "td", "th", "pre", "blockquote"]

Pairs = list[tuple[str, list[str]]]


def _to_sections(pairs: Pairs, separator: str) -> list[ExtractedSection]:
    sections = []
    for heading, parts in pairs:
        body = separator.join(parts).strip()
        if body:
            sections.append(ExtractedSection(heading=heading, text=body))
    return sections


def _split_markdown(text: str) -> list[ExtractedSection]:
    pairs: Pairs = [("", [])]
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.*\S)\s*$", line)
        if match:
            pairs.append((match.group(1), []))
        else:
            pairs[-1][1].append(line)
    return _to_sections(pairs, "\n")


def _split_html(html: str) -> list[ExtractedSection]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")
    pairs: Pairs = [("", [])]
    for element in soup.find_all(HEADING_TAGS + BLOCK_TAGS):
        if not isinstance(element, Tag) or element.find_parent(BLOCK_TAGS):
            continue
        text = re.sub(r"\s+", " ", element.get_text()).strip()
        if not text:
            continue
        if element.name in HEADING_TAGS:
            pairs.append((text, []))
        else:
            pairs[-1][1].append(text)
    return _to_sections(pairs, "\n\n")


def extract_document(filename: str, data: bytes) -> list[ExtractedSection]:
    """Extract sections from .txt, .md or .html bytes."""
    text = data.decode("utf-8-sig")
    extension = PurePosixPath(filename).suffix.lower()
    if extension in {".html", ".htm"}:
        sections = _split_html(text)
    elif extension == ".md":
        sections = _split_markdown(text)
    else:
        sections = _to_sections([("", text.splitlines())], "\n")
    if not sections:
        raise ValueError("no readable text found in the document")
    return sections