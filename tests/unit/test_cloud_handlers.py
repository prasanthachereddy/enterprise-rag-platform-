import json
from decimal import Decimal
from typing import Any

import pytest

from enterprise_rag.cloud.api_handler import create_upload, get_status
from enterprise_rag.cloud.process_handler import process_object
from enterprise_rag.cloud.trigger_handler import execution_name, process_batch, s3_objects

HTML = (
    b"<h1>Leave Policy</h1><h2>Annual Leave</h2>"
    b"<p>Full-time employees receive 24 days of paid annual leave per calendar year.</p>"
)


class FakeS3:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)
        self.presign_calls: list[dict[str, Any]] = []

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        return {"ContentLength": len(self.objects[Key])}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        data = self.objects[Key]

        class Body:
            def read(self) -> bytes:
                return data

        return {"Body": Body()}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        self.objects[Key] = Body

    def generate_presigned_url(self, op: str, Params: dict[str, str], ExpiresIn: int) -> str:
        self.presign_calls.append({"op": op, "params": Params, "expires": ExpiresIn})
        return f"https://example.invalid/{Params['Key']}?expires={ExpiresIn}"


def run(s3: FakeS3, key: str, max_bytes: int = 10_000) -> dict[str, str]:
    return process_object(s3, "bkt", key, 900, 120, max_bytes)


def test_process_writes_chunks_and_returns_only_a_small_status() -> None:
    s3 = FakeS3({"uploads/ab12-leave.html": HTML})
    result = run(s3, "uploads/ab12-leave.html")
    assert result["status"] == "PROCESSED"
    assert result["chunk_count"] == "1"
    assert result["output_key"] == f"processed/{result['document_id']}/chunks.jsonl"
    line = json.loads(s3.objects[result["output_key"]].decode().splitlines()[0])
    assert line["heading"] == "Annual Leave"
    assert "24 days" not in json.dumps(result)


def test_same_content_gives_the_same_document_and_output_key() -> None:
    s3 = FakeS3({"uploads/a-one.html": HTML, "uploads/b-two.html": HTML})
    first = run(s3, "uploads/a-one.html")
    second = run(s3, "uploads/b-two.html")
    assert first["output_key"] == second["output_key"]


@pytest.mark.parametrize(
    ("key", "data", "reason"),
    [
        ("uploads/a-virus.exe", b"text", "unsupported"),
        ("uploads/a-empty.txt", b"   ", "empty"),
        ("uploads/a-big.txt", b"x" * 50, "too large"),
        ("uploads/a-empty.html", b"<html><body></body></html>", "no readable text"),
        ("elsewhere/a.txt", b"hello", "unexpected object location"),
    ],
)
def test_bad_files_are_rejected_not_crashed(key: str, data: bytes, reason: str) -> None:
    result = run(FakeS3({key: data}), key, max_bytes=40)
    assert result["status"] == "REJECTED"
    assert reason in result["reason"]


def sqs_event(*bodies: str) -> dict[str, Any]:
    return {"Records": [{"messageId": f"m{i}", "body": b} for i, b in enumerate(bodies)]}


def s3_body(key: str = "uploads/a-my+file.txt", etag: str = "e1") -> str:
    obj = {"key": key, "eTag": etag}
    return json.dumps({"Records": [{"s3": {"bucket": {"name": "bkt"}, "object": obj}}]})


class FakeSfn:
    def __init__(self, fail_with: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_with = fail_with

    def start_execution(self, **kwargs: Any) -> None:
        if self.fail_with:
            raise self.fail_with
        self.calls.append(kwargs)


class AwsError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def test_trigger_starts_one_named_run_and_decodes_the_key() -> None:
    sfn = FakeSfn()
    result = process_batch(sqs_event(s3_body()), sfn, "arn:sm")
    assert result == {"batchItemFailures": []}
    call = sfn.calls[0]
    assert call["name"] == execution_name("bkt", "uploads/a-my file.txt", "e1")
    assert json.loads(call["input"]) == {"bucket": "bkt", "key": "uploads/a-my file.txt"}


def test_trigger_treats_an_already_started_run_as_success() -> None:
    result = process_batch(sqs_event(s3_body()), FakeSfn(AwsError("ExecutionAlreadyExists")), "a")
    assert result == {"batchItemFailures": []}


def test_trigger_skips_s3_test_events() -> None:
    sfn = FakeSfn()
    body = json.dumps({"Service": "Amazon S3", "Event": "s3:TestEvent"})
    assert process_batch(sqs_event(body), sfn, "a") == {"batchItemFailures": []}
    assert sfn.calls == []
    assert s3_objects(body) == []


def test_trigger_reports_only_the_failed_messages() -> None:
    result = process_batch(sqs_event(s3_body(), "not json"), FakeSfn(), "a")
    assert result == {"batchItemFailures": [{"itemIdentifier": "m1"}]}
    broken = process_batch(sqs_event(s3_body()), FakeSfn(AwsError("Throttling")), "a")
    assert broken == {"batchItemFailures": [{"itemIdentifier": "m0"}]}


def test_upload_link_uses_a_clean_name_and_short_expiry() -> None:
    s3 = FakeS3({})
    reply = create_upload(json.dumps({"filename": r"..\x\Policy v2.MD"}), s3, "bkt", lambda: "id1")
    body = json.loads(reply["body"])
    assert reply["statusCode"] == 200
    assert body["key"] == "uploads/id1-Policy v2.MD"
    assert s3.presign_calls[0]["params"] == {"Bucket": "bkt", "Key": body["key"]}
    assert s3.presign_calls[0]["expires"] == 300


@pytest.mark.parametrize("body", [None, "{bad", "[]", '{"filename": 5}', '{"filename": "a.exe"}'])
def test_upload_link_rejects_bad_requests(body: str | None) -> None:
    assert create_upload(body, FakeS3({}), "bkt")["statusCode"] == 400


class FakeTable:
    def __init__(self, item: dict[str, Any] | None) -> None:
        self.item = item

    def get_item(self, Key: dict[str, str]) -> dict[str, Any]:
        return {"Item": self.item} if self.item else {}


def test_status_returns_the_audit_row_with_plain_numbers() -> None:
    table = FakeTable({"source_key": "uploads/a", "status": "PROCESSED", "chunk_count": Decimal(2)})
    reply = get_status({"key": "uploads/a"}, table)
    assert reply["statusCode"] == 200
    assert json.loads(reply["body"])["chunk_count"] == 2


def test_status_handles_missing_and_invalid_keys() -> None:
    assert get_status({"key": "uploads/a"}, FakeTable(None))["statusCode"] == 404
    assert get_status({"key": "other/a"}, FakeTable(None))["statusCode"] == 400
    assert get_status(None, FakeTable(None))["statusCode"] == 400