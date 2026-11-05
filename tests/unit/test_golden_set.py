from pathlib import Path

from enterprise_rag.config import Settings, project_root
from enterprise_rag.evaluation.golden import load_golden
from enterprise_rag.ingestion.registry import Registry
from enterprise_rag.ingestion.service import ingest_file


def corpus_sections(tmp_path: Path) -> dict[tuple[str, str], str]:
    """Ingest both document folders and join the chunk text of each section."""
    settings = Settings(_env_file=None)
    registry = Registry(tmp_path / "registry.json")
    sections: dict[tuple[str, str], str] = {}
    for folder in ("sample_docs", "eval_docs"):
        for path in sorted((project_root() / "data" / folder).glob("*")):
            for chunk in ingest_file(path, settings, registry).chunks:
                key = (chunk.source_filename, chunk.heading)
                sections[key] = sections.get(key, "") + " " + chunk.text
    return sections


def test_every_golden_label_points_at_a_real_section_containing_its_facts(tmp_path: Path) -> None:
    sections = corpus_sections(tmp_path)
    questions = load_golden(project_root() / "data" / "eval" / "golden.jsonl")
    for question in questions:
        if not question.answerable:
            continue
        text = sections[(question.source, question.heading)].lower()
        for fact in question.must_contain:
            assert fact.lower() in text, f"{question.id}: '{fact}' not in its section"


def test_golden_set_has_the_expected_shape(tmp_path: Path) -> None:
    questions = load_golden(project_root() / "data" / "eval" / "golden.jsonl")
    assert len(questions) == 30
    assert sum(q.answerable for q in questions) == 24
    documents = {source for source, _ in corpus_sections(tmp_path)}
    assert len(documents) == 15
    assert len({q.question for q in questions}) == 30