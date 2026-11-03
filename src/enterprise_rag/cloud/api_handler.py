"""Lambda behind the HTTP API: hand out upload links and report processing status."""

import json
import os
import uuid
from collections.abc import Callable
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from enterprise_rag.ingestion.validation import (
    ALLOWED_EXTENSIONS,
    ValidationError,
    sanitize_filename,
)

UPLOAD_EXPIRES_SECONDS = 300
MAX_KEY_CHARS = 300


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def create_upload(
    body: str | None, s3: Any, bucket: str, new_id: Callable[[], str] = _new_id
) -> dict[str, Any]:
    """Return a short-lived link the caller can PUT one file to."""
    try:
        payload = json.loads(body or "")
    except ValueError:
        return _response(400, {"error": "body must be JSON"})
    filename = payload.get("filename") if isinstance(payload, dict) else None
    if not isinstance(filename, str):
        return _response(400, {"error": "filename is required"})
    try:
        clean = sanitize_filename(filename)
    except ValidationError as exc:
        return _response(400, {"error": str(exc)})
    if PurePosixPath(clean).suffix.lower() not in ALLOWED_EXTENSIONS:
        return _response(400, {"error": "unsupported file type"})
    key = f"uploads/{new_id()}-{clean}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=UPLOAD_EXPIRES_SECONDS,
    )
    return _response(200, {"key": key, "upload_url": url, "expires_in": UPLOAD_EXPIRES_SECONDS})


def get_status(params: dict[str, str] | None, table: Any) -> dict[str, Any]:
    """Return the audit record for one uploaded file."""
    key = (params or {}).get("key", "")
    if not key.startswith("uploads/") or len(key) > MAX_KEY_CHARS:
        return _response(400, {"error": "key must be an uploads/ key"})
    item = table.get_item(Key={"source_key": key}).get("Item")
    if not item:
        return _response(404, {"status": "NOT_FOUND"})
    plain = {name: int(v) if isinstance(v, Decimal) else v for name, v in item.items()}
    return _response(200, plain)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    import boto3
    from botocore.config import Config

    route = event.get("routeKey", "")
    if route == "POST /uploads":
        region = os.environ["AWS_REGION"]
        s3 = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=f"https://s3.{region}.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )
        return create_upload(event.get("body"), s3, os.environ["BUCKET_NAME"])
    if route == "GET /status":
        table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
        return get_status(event.get("queryStringParameters"), table)
    return _response(404, {"error": "not found"})