"""Lambda task: read one uploaded file from S3, validate it, chunk it, write the chunks back."""

import json
import logging
import os
from typing import Any

from enterprise_rag.ingestion.chunking import chunk_sections
from enterprise_rag.ingestion.extract import extract_document
from enterprise_rag.ingestion.registry import create_record
from enterprise_rag.ingestion.validation import validate_upload
from enterprise_rag.observability.logging_config import configure_logging, log_event

LOGGER = logging.getLogger(__name__)
UPLOAD_PREFIX = "uploads/"


def _rejected(key: str, reason: str) -> dict[str, str]:
    return {"status": "REJECTED", "source_key": key, "reason": reason}


def process_object(
    s3: Any, bucket: str, key: str, chunk_size: int, chunk_overlap: int, max_bytes: int
) -> dict[str, str]:
    """Return a small status dictionary. Document text never leaves this function."""
    if not key.startswith(UPLOAD_PREFIX):
        return _rejected(key, "unexpected object location")
    head = s3.head_object(Bucket=bucket, Key=key)
    if int(head["ContentLength"]) > max_bytes:
        return _rejected(key, "file is too large")
    data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    try:
        clean = validate_upload(key.rsplit("/", 1)[-1], data, max_bytes)
        sections = extract_document(clean, data)
    except ValueError as exc:
        return _rejected(key, str(exc))
    record = create_record(clean, data)
    chunks = chunk_sections(sections, record.document_id, clean, chunk_size, chunk_overlap)
    output_key = f"processed/{record.document_id}/chunks.jsonl"
    lines = (json.dumps(chunk.to_dict(), ensure_ascii=False) for chunk in chunks)
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=("\n".join(lines) + "\n").encode("utf-8"),
        ContentType="application/x-ndjson",
    )
    return {
        "status": "PROCESSED",
        "source_key": key,
        "document_id": record.document_id,
        # A string on purpose: Step Functions passes it to DynamoDB as a number ("N").
        "chunk_count": str(len(chunks)),
        "output_key": output_key,
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, str]:
    import boto3

    configure_logging("INFO")
    result = process_object(
        boto3.client("s3"),
        event["bucket"],
        event["key"],
        int(os.environ.get("CHUNK_SIZE", "900")),
        int(os.environ.get("CHUNK_OVERLAP", "120")),
        int(os.environ.get("MAX_UPLOAD_BYTES", "10485760")),
    )
    log_event(LOGGER, logging.INFO, "document_processed", status=result["status"])
    return result