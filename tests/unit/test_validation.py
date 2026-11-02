import pytest

from enterprise_rag.ingestion.validation import (
    ValidationError,
    sanitize_filename,
    validate_upload,
)


def test_sanitize_removes_folders_and_unsafe_characters() -> None:
    assert sanitize_filename(r"..\private\policy.html") == "policy.html"
    assert sanitize_filename("../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename("policy<>.html") == "policy_.html"


def test_sanitize_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        sanitize_filename("..")


def test_valid_upload_returns_clean_name() -> None:
    assert validate_upload("a/b/Policy.MD", b"# Title\nText", 1000) == "Policy.MD"


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("virus.exe", b"text", "unsupported"),
        ("a.txt", b"   ", "empty"),
        ("a.txt", b"x" * 20, "too large"),
        ("a.txt", b"abc\x00def", "binary"),
        ("a.txt", b"\xff\xfa\xfb", "UTF-8"),
    ],
)
def test_bad_uploads_are_rejected(name: str, data: bytes, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_upload(name, data, 10 if message == "too large" else 1000)