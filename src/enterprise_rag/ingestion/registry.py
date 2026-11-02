"""Document identity and a small JSON registry of ingested documents."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from enterprise_rag.ingestion.models import DocumentRecord


def make_document_id(data: bytes) -> str:
    return "doc-" + hashlib.sha256(data).hexdigest()[:16]


def create_record(filename: str, data: bytes) -> DocumentRecord:
    return DocumentRecord(
        document_id=make_document_id(data),
        filename=filename,
        extension=PurePosixPath(filename).suffix.lower(),
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        created_at=datetime.now(UTC).isoformat(),
    )


class Registry:
    """Stores one record per document ID in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.path.is_file():
            return {}
        loaded: dict[str, dict[str, object]] = json.loads(self.path.read_text(encoding="utf-8"))
        return loaded

    def add(self, record: DocumentRecord) -> bool:
        """Save the record. Return False if this document was already registered."""
        records = self._load()
        if record.document_id in records:
            return False
        records[record.document_id] = asdict(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return True

    def get(self, document_id: str) -> dict[str, object] | None:
        return self._load().get(document_id)