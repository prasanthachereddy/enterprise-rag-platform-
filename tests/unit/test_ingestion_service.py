from pathlib import Path

from enterprise_rag.config import Settings, project_root
from enterprise_rag.ingestion.registry import Registry, make_document_id
from enterprise_rag.ingestion.service import ingest_bytes, ingest_file

SETTINGS = Settings(_env_file=None, chunk_size=300, chunk_overlap=40)


def test_document_id_is_stable_and_content_based() -> None:
    assert make_document_id(b"abc") == make_document_id(b"abc")
    assert make_document_id(b"abc") != make_document_id(b"abd")
    assert make_document_id(b"abc").startswith("doc-")


def test_second_upload_of_same_bytes_is_not_new(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "registry.json")
    first = ingest_bytes("a.txt", b"Hello world.", SETTINGS, registry)
    second = ingest_bytes("b.txt", b"Hello world.", SETTINGS, Registry(tmp_path / "registry.json"))
    assert first.is_new is True
    assert second.is_new is False
    assert first.record.document_id == second.record.document_id
    assert registry.get(first.record.document_id) is not None


def test_sample_documents_ingest_with_headings(tmp_path: Path) -> None:
    registry = Registry(tmp_path / "registry.json")
    folder = project_root() / "data" / "sample_docs"
    results = {p.name: ingest_file(p, SETTINGS, registry) for p in sorted(folder.glob("*"))}
    assert set(results) == {"expense_policy.txt", "leave_policy.html", "security_policy.md"}
    assert all(result.chunks for result in results.values())
    headings = {chunk.heading for chunk in results["leave_policy.html"].chunks}
    assert headings == {"Annual Leave", "Sick Leave"}