"""Application configuration, loaded from environment variables / .env."""
from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Metadata
    project_name: str = "Price Pantry API"
    api_version: str = "0.1.0"

    # Database — default targets a locally running Postgres; Docker overrides
    # this via the DATABASE_URL env var (host = the `db` service).
    database_url: str = Field(
        default="postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"
    )

    # CORS — comma-separated origins allowed to call the API.
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalize_driver(cls, v: str) -> str:
        # Accept a plain postgres URL and upgrade it to the psycopg (v3) driver.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


settings = Settings()
