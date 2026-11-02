"""Upload checks: safe file name, allowed type, size, and readable text."""

import re
from pathlib import PurePosixPath, PureWindowsPath

ALLOWED_EXTENSIONS = {".txt", ".md", ".html", ".htm"}


class ValidationError(ValueError):
    """Raised when an upload is not acceptable."""


def sanitize_filename(filename: str) -> str:
    """Drop any folder part and replace unsafe characters."""
    name = PureWindowsPath(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    if not name:
        raise ValidationError("file name is empty after cleaning")
    return name[:120]


def validate_upload(filename: str, data: bytes, max_bytes: int) -> str:
    """Return the cleaned file name, or raise ValidationError."""
    clean = sanitize_filename(filename)
    extension = PurePosixPath(clean).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"unsupported file type: {extension or 'none'}")
    if not data.strip():
        raise ValidationError("file is empty")
    if len(data) > max_bytes:
        raise ValidationError("file is too large")
    if b"\x00" in data:
        raise ValidationError("file looks binary")
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("file is not valid UTF-8 text") from exc
    return clean