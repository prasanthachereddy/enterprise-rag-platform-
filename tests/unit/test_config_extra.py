import pytest
from pydantic import ValidationError

from enterprise_rag.config import Settings


def test_min_query_coverage_default_is_half() -> None:
    assert Settings(_env_file=None).min_query_coverage == 0.5


def test_min_query_coverage_must_be_between_zero_and_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIN_QUERY_COVERAGE", "1.5")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)