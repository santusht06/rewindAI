"""Configuration management for Rewind backend service.

Implements NFR-SEC-001 (secrets stored server-side), NFR-PRIV-001 (redaction).
"""

from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with strict typing and secret masking."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    app_name: str = "Rewind AI Companion API"
    environment: Literal["development", "testing", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_v1_prefix: str = "/api/v1"

    # Security & Cryptographic Secrets
    secret_key: SecretStr = Field(
        default=SecretStr("dev-insecure-secret-key-32-characters-minimum"),
        description="Master secret key for server-issued nonces and session validation",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./rewind_local.db",
        description="Connection URL for PostgreSQL+pgvector or SQLite test harness",
    )

    # AI Provider Keys (Optional: when unset, deterministic Mock Provider is used)
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # Guardrails & Invariants
    spoiler_default_mode: Literal["safe", "full"] = "safe"
    max_context_tokens: int = Field(default=4000, ge=500, le=32000)
    max_question_length: int = Field(default=500, ge=10, le=2000)
    confirmation_nonce_expire_seconds: int = Field(default=300, ge=30, le=3600)

    # Verification helper for diagnostics
    def is_production(self) -> bool:
        return self.environment == "production"

    def has_gemini_provider(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value())

    def has_openai_provider(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value())


# Singleton instance
settings = Settings()
