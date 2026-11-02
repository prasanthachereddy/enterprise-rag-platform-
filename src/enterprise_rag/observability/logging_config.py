"""JSON logging that never writes secrets or document content."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_PARTS = ("password", "secret", "token", "api_key", "authorization", "credential")
CONTENT_KEYS = {"text", "prompt", "answer", "question", "document_text", "content", "body"}


def redact(value: Any) -> Any:
    """Return a copy of value with secrets and document content hidden."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in CONTENT_KEYS or any(part in lowered for part in SENSITIVE_PARTS):
                cleaned[str(key)] = REDACTED
            else:
                cleaned[str(key)] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Write one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            event["fields"] = redact(fields)
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Send all logs to standard output as JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """Log a message with extra named fields, for example log_event(log, INFO, "x", doc="d1")."""
    logger.log(level, message, extra={"fields": fields})