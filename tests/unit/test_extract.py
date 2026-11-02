import pytest

from enterprise_rag.ingestion.extract import extract_document


def test_html_headings_and_paragraphs() -> None:
    html = b"<h1>Top</h1><h2>A</h2><p>One <b>bold</b>, two.</p><p>Three.</p><h2>B</h2><p>Four.</p>"
    sections = extract_document("x.html", html)
    assert [s.heading for s in sections] == ["A", "B"]
    assert sections[0].text == "One bold, two.\n\nThree."


def test_html_ignores_scripts_and_keeps_line_breaks() -> None:
    html = b"<p>line1<br>line2</p><script>alert(1)</script>"
    sections = extract_document("x.html", html)
    assert "alert" not in sections[0].text
    assert "line1 line2" in " ".join(sections[0].text.split())


def test_markdown_headings() -> None:
    sections = extract_document("x.md", b"# T\n\n## A\nHello.\n\n## B\nWorld.")
    assert [(s.heading, s.text) for s in sections] == [("A", "Hello."), ("B", "World.")]


def test_plain_text_is_one_section_without_heading() -> None:
    sections = extract_document("x.txt", b"First.\n\nSecond.")
    assert len(sections) == 1
    assert sections[0].heading == ""


def test_document_without_text_is_rejected() -> None:
    with pytest.raises(ValueError, match="no readable text"):
        extract_document("x.html", b"<html><body></body></html>")