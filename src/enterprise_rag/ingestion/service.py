"""Run validation, extraction, chunking and registration for one document."""

import logging
from dataclasses import dataclass
from pathlib import Path

from enterprise_rag.config import Settings
from enterprise_rag.ingestion.chunking import chunk_sections
from enterprise_rag.ingestion.extract import extract_document
from enterprise_rag.ingestion.models import Chunk, DocumentRecord
from enterprise_rag.ingestion.registry import Registry, create_record
from enterprise_rag.ingestion.validation import validate_upload
from enterprise_rag.observability.logging_config import log_event

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    record: DocumentRecord
    chunks: list[Chunk]
    is_new: bool


def ingest_bytes(
    filename: str, data: bytes, settings: Settings, registry: Registry
) -> IngestionResult:
    clean_name = validate_upload(filename, data, settings.max_upload_bytes)
    sections = extract_document(clean_name, data)
    record = create_record(clean_name, data)
    chunks = chunk_sections(
        sections, record.document_id, clean_name, settings.chunk_size, settings.chunk_overlap
    )
    is_new = registry.add(record)
    log_event(
        LOGGER,
        logging.INFO,
        "document_ingested",
        document_id=record.document_id,
        chunk_count=len(chunks),
        is_new=is_new,
    )
    return IngestionResult(record=record, chunks=chunks, is_new=is_new)


def ingest_file(path: Path, settings: Settings, registry: Registry) -> IngestionResult:
    return ingest_bytes(path.name, path.read_bytes(), settings, registry)