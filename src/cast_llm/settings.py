"""Environment-backed settings for cast-llm (MongoDB, etc.)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils import get_project_root


class CastLlmSettings(BaseSettings):
    """Load from environment with prefix ``CAST_LLM_`` (optional ``.env``)."""

    model_config = SettingsConfigDict(
        env_prefix="CAST_LLM_",
        # Resolve from repo root so ``CAST_LLM_*`` loads when cwd is ``notebooks/``
        # (e.g. nbconvert / Jupyter) instead of only when cwd is the project root.
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "castnet"
    reports_collection: str = "reports"
    handover_glossary_enabled: bool = True
    handover_glossary_path: str = "artifacts/shift_glossary/finalglossary.json"


@lru_cache
def get_settings() -> CastLlmSettings:
    """Return cached settings (reload process to pick up env changes)."""
    return CastLlmSettings()
