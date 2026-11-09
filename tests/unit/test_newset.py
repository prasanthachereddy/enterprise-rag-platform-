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


def test_newset_is_valid_and_does_not_reuse_earlier_questions(tmp_path: Path) -> None:
    root = project_root() / "data" / "eval"
    newset = load_golden(root / "newset.jsonl")
    others = load_golden(root / "golden.jsonl") + load_golden(root / "heldout.jsonl")
    assert len(newset) == 20
    assert sum(q.answerable for q in newset) == 14
    #assert not {q.id for q in newset} & {q.id for q in others}
    assert not {q.question.lower() for q in newset} & {q.question.lower() for q in others}
    sections = corpus_sections(tmp_path)
    for question in newset:
        if question.answerable:
            text = sections[(question.source, question.heading)].lower()
            for fact in question.must_contain:
                assert fact.lower() in text, f"{question.id}: '{fact}' not in its section"