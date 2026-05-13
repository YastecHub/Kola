from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_database_url: str = Field(..., alias="SUPABASE_DATABASE_URL")
    squad_secret_key: str = Field(..., alias="SQUAD_SECRET_KEY")
    squad_public_key: str = Field(..., alias="SQUAD_PUBLIC_KEY")
    squad_base_url: AnyHttpUrl = Field("https://sandbox-api-d.squadco.com", alias="SQUAD_BASE_URL")
    squad_mock_mode: bool = Field(False, alias="SQUAD_MOCK_MODE")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    squad_beneficiary_account: str | None = Field(default=None, alias="SQUAD_BENEFICIARY_ACCOUNT")
    environment: str = Field("development", alias="ENVIRONMENT")
    api_key: str = Field("change-me", alias="API_KEY")
    backend_cors_origins: str = Field("", alias="BACKEND_CORS_ORIGINS")
    kola_score_api_rate_limit_per_minute: int = Field(60, alias="KOLA_SCORE_API_RATE_LIMIT_PER_MINUTE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if not self.backend_cors_origins:
            return []
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def squad_webhook_secret(self) -> str:
        return self.webhook_secret or self.squad_secret_key

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.supabase_database_url.startswith("postgresql://"):
            return self.supabase_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.supabase_database_url.startswith("postgres://"):
            return self.supabase_database_url.replace("postgres://", "postgresql+psycopg://", 1)
        return self.supabase_database_url


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing_fields = [
            ".".join(str(part) for part in error["loc"])
            for error in exc.errors()
            if error.get("type") == "missing"
        ]
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise RuntimeError(f"Missing required environment variable(s): {fields}") from exc
        raise


settings = get_settings()
