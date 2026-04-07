"""Environment-backed settings for cast-llm (MongoDB, etc.)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CastLlmSettings(BaseSettings):
    """Load from environment with prefix ``CAST_LLM_`` (optional ``.env``)."""

    model_config = SettingsConfigDict(
        env_prefix="CAST_LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "castnet"
    reports_collection: str = "reports"


@lru_cache
def get_settings() -> CastLlmSettings:
    """Return cached settings (reload process to pick up env changes)."""
    return CastLlmSettings()
