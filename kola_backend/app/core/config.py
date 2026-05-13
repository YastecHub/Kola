from __future__ import annotations

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_database_url: str = Field(..., alias="SUPABASE_DATABASE_URL")
    squad_secret_key: str = Field(..., alias="SQUAD_SECRET_KEY")
    squad_public_key: str = Field(..., alias="SQUAD_PUBLIC_KEY")
    squad_base_url: AnyHttpUrl = Field("https://sandbox-api-d.squadco.com", alias="SQUAD_BASE_URL")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    squad_beneficiary_account: str | None = Field(default=None, alias="SQUAD_BENEFICIARY_ACCOUNT")
    environment: str = Field("development", alias="ENVIRONMENT")
    api_key: str = Field("change-me", alias="API_KEY")
    backend_cors_origins: list[str] = Field(default_factory=list, alias="BACKEND_CORS_ORIGINS")
    kola_score_api_rate_limit_per_minute: int = Field(60, alias="KOLA_SCORE_API_RATE_LIMIT_PER_MINUTE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def squad_webhook_secret(self) -> str:
        return self.webhook_secret or self.squad_secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
