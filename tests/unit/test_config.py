from pathlib import Path

import pytest
from pydantic import ValidationError

from enterprise_rag.config import Settings, project_root


def test_chunk_defaults_are_valid() -> None:
    settings = Settings(_env_file=None)
    assert settings.chunk_size > 0
    assert 0 <= settings.chunk_overlap < settings.chunk_size


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="smaller"):
        Settings(_env_file=None, chunk_size=500, chunk_overlap=500)


def test_environment_variable_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHUNK_SIZE", "500")
    monkeypatch.setenv("CHUNK_OVERLAP", "50")
    settings = Settings(_env_file=None)
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50


def test_log_level_is_normalised_to_upper_case(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LOG_LEVEL", "debug")
    assert Settings(_env_file=None).app_log_level == "DEBUG"


def test_invalid_answer_mode_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANSWER_MODE", "magic")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_project_root_contains_pyproject() -> None:
    assert (project_root() / "pyproject.toml").is_file()
    assert isinstance(project_root(), Path)

def test_env_example_file_loads_cleanly() -> None:
    settings = Settings(_env_file=project_root() / ".env.example")
    assert settings.bedrock_embedding_dimensions == 1024
    assert settings.answer_mode == "offline"


def test_invalid_embedding_dimensions_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_EMBEDDING_DIMENSIONS", "999")
    with pytest.raises(ValidationError, match="256, 512 or 1024"):
        Settings(_env_file=None)    