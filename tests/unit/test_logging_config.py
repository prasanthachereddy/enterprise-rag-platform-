import json
import logging

import pytest

from enterprise_rag.observability.logging_config import (
    REDACTED,
    JsonFormatter,
    configure_logging,
    log_event,
    redact,
)


def make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_formatter_outputs_valid_json() -> None:
    parsed = json.loads(JsonFormatter().format(make_record("unit test")))
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "unit test"
    assert "timestamp" in parsed


def test_redact_hides_secrets_and_document_content() -> None:
    cleaned = redact({"password": "p", "aws_secret_key": "s", "text": "body", "document_id": "d1"})
    assert cleaned["password"] == REDACTED
    assert cleaned["aws_secret_key"] == REDACTED
    assert cleaned["text"] == REDACTED
    assert cleaned["document_id"] == "d1"


def test_redact_works_on_nested_values() -> None:
    cleaned = redact({"outer": {"token": "t", "items": [{"prompt": "x", "ok": 1}]}})
    assert cleaned["outer"]["token"] == REDACTED
    assert cleaned["outer"]["items"][0]["prompt"] == REDACTED
    assert cleaned["outer"]["items"][0]["ok"] == 1


def test_log_event_writes_redacted_fields(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    log = logging.getLogger("phase0")
    log_event(log, logging.INFO, "ingested", document_id="d1", text="SECRET")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    parsed = json.loads(line)
    assert parsed["message"] == "ingested"
    assert parsed["fields"]["document_id"] == "d1"
    assert parsed["fields"]["text"] == REDACTED
    assert "SECRET" not in line