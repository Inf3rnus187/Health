"""Application configuration loaded from environment variables.

Single source of truth for runtime settings. No secret is hard-coded;
every value comes from the environment (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    cors_origins: list[str] = Field(default_factory=list)

    media_dir: str = "/data/media"
    exports_dir: str = "/data/exports"

    default_timezone: str = "Europe/Paris"
    default_unit_system: str = "metric"

    ollama_url: str = "http://host.docker.internal:11434"
    ollama_text_model: str = "llama3.1"
    ollama_vision_model: str = "llava"
    photo_prompt_version: str = "v1"
    max_upload_mb: int = 15
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
