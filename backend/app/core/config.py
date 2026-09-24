"""Application configuration loaded from environment variables.

Single source of truth for runtime settings. No secret is hard-coded;
every value comes from the environment (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings, validated once at startup."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Phoenix Health Hub"
    env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    secret_key: str = Field(min_length=32)
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 14
    jwt_algorithm: str = "HS256"

    database_url: str = "postgresql+asyncpg://phoenix:phoenix@db:5432/phoenix"
    redis_url: str = "redis://redis:6379/0"

    # NoDecode: take the raw env string (empty or CSV) rather than letting
    # pydantic-settings JSON-decode it, then split it in the validator.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    media_dir: str = "/data/media"
    exports_dir: str = "/data/exports"
    #: Shared with ./update.sh on the host (update status, requests).
    update_dir: str = "/data/update"

    default_timezone: str = "Europe/Paris"
    default_unit_system: str = "metric"

    ollama_url: str = "http://host.docker.internal:11434"
    # Clinical reasoning / synthesis (text), e.g. medgemma:27b.
    ollama_text_model: str = "llama3.1"
    # Photos (image), e.g. medgemma1.5 (MedGemma 1.5 4B multimodal).
    ollama_vision_model: str = "llava"
    # Reading medical documents (lab reports, FibroScan…); empty = the
    # vision model, which also reads scanned pages.
    ollama_document_model: str = ""
    max_upload_mb: int = 15
    #: Look a packaged food up by its barcode on Open Food Facts (only
    #: the barcode leaves the hub). Off by default: nothing goes out.
    food_lookup_online: bool = False
    openfoodfacts_url: str = "https://world.openfoodfacts.org"
    media_encryption_key: str | None = None
    mfa_issuer: str = "Phoenix Health Hub"
    retention_days: int = 0

    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-please"

    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string for CORS origins."""
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached ``Settings`` instance."""
    return Settings()  # type: ignore[call-arg]
