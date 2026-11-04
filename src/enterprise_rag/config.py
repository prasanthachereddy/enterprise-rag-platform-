"""Application settings, read from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """All configuration in one place. Field names map to upper-case environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "enterprise-rag-platform"
    app_env: Literal["local", "dev", "prod"] = "local"
    app_log_level: LogLevel = "INFO"

    # Chunking and uploads (Phase 1)
    chunk_size: int = Field(default=900, ge=100, le=8000)
    chunk_overlap: int = Field(default=120, ge=0, le=2000)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)

    # OpenSearch (Phase 2)
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "enterprise-policy-chunks"

    # Bedrock (Phases 2 and 3)
    aws_region: str = "ap-south-1"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_embedding_dimensions: int = 1024
    bedrock_chat_model_id: str = "in.anthropic.claude-haiku-4-5-20251001-v1:0"
    answer_max_tokens: int = Field(default=400, ge=50, le=2000)

    # Retrieval and answers (Phases 2 and 3)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    answer_mode: Literal["offline", "bedrock"] = "offline"
    # Local embeddings through Text Embeddings Inference in Docker (Phase 2)
    local_embedding_url: str = "http://localhost:8080"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    local_embedding_dimensions: int = Field(default=384, ge=8, le=4096)
    retrieval_candidates: int = Field(default=20, ge=1, le=200)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    min_query_coverage: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @field_validator("app_log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("bedrock_embedding_dimensions")
    @classmethod
    def _check_embedding_dimensions(cls, value: int) -> int:
        if value not in {256, 512, 1024}:
            raise ValueError("bedrock_embedding_dimensions must be 256, 512 or 1024")
        return value

    @model_validator(mode="after")
    def _check_chunk_settings(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the settings, created once and then reused."""
    return Settings()


def clear_settings_cache() -> None:
    """Forget the cached settings (used by tests)."""
    get_settings.cache_clear()

def project_root() -> Path:
    """Return the repository root (config.py lives in src/enterprise_rag)."""
    return Path(__file__).resolve().parents[2]        
