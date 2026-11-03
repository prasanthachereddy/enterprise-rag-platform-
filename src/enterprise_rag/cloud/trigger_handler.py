"""Lambda: read S3 notifications from SQS and start one Step Functions run per uploaded file."""

import hashlib
import json
import logging
import os
from typing import Any
from urllib.parse import unquote_plus

from enterprise_rag.observability.logging_config import configure_logging, log_event

LOGGER = logging.getLogger(__name__)


def execution_name(bucket: str, key: str, etag: str) -> str:
    """Same upload event, same name: Step Functions then refuses a second identical run."""
    return hashlib.sha256(f"{bucket}/{key}/{etag}".encode()).hexdigest()[:40]


def s3_objects(body: str) -> list[dict[str, str]]:
    """List the uploaded objects named in one SQS message body (S3 test events have none)."""
    payload = json.loads(body)
    objects = []
    for record in payload.get("Records", []):
        s3 = record["s3"]
        objects.append(
            {
                "bucket": s3["bucket"]["name"],
                "key": unquote_plus(s3["object"]["key"]),
                "etag": s3["object"].get("eTag", ""),
            }
        )
    return objects


def _error_code(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str(response.get("Error", {}).get("Code", ""))
    return ""


def start_run(sfn: Any, state_machine_arn: str, item: dict[str, str]) -> bool:
    """Start a run. Return False when this exact upload event was already started."""
    try:
        sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name(item["bucket"], item["key"], item["etag"]),
            input=json.dumps({"bucket": item["bucket"], "key": item["key"]}),
        )
    except Exception as exc:
        if _error_code(exc) == "ExecutionAlreadyExists":
            return False
        raise
    return True


def process_batch(event: dict[str, Any], sfn: Any, state_machine_arn: str) -> dict[str, Any]:
    """Return SQS partial-batch failures so only the bad messages are retried."""
    failures: list[dict[str, str]] = []
    started = 0
    for record in event.get("Records", []):
        try:
            for item in s3_objects(record["body"]):
                started += int(start_run(sfn, state_machine_arn, item))
        except Exception as exc:
            LOGGER.warning("message_failed: %s", type(exc).__name__)
            failures.append({"itemIdentifier": record["messageId"]})
    log_event(LOGGER, logging.INFO, "batch_done", started=started, failed=len(failures))
    return {"batchItemFailures": failures}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    import boto3

    configure_logging("INFO")
    return process_batch(event, boto3.client("stepfunctions"), os.environ["STATE_MACHINE_ARN"])