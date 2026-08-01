from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "telegram-bot-platform"
    app_env: Literal["development", "test", "staging", "production"] = "production"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_version: str = "1.0.0"

    public_base_url: AnyHttpUrl
    database_url: SecretStr
    bot_credential_keys: SecretStr
    admin_api_key: SecretStr
    log_level: str = "INFO"

    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_timeout: float = Field(default=30, gt=0)
    db_pool_recycle: int = Field(default=1800, ge=0)

    telegram_http_timeout: float = Field(default=10, gt=0)
    telegram_http_connect_timeout: float = Field(default=5, gt=0)
    telegram_http_max_connections: int = Field(default=100, ge=1)
    telegram_http_keepalive_connections: int = Field(default=20, ge=1)
    telegram_safe_retry_attempts: int = Field(default=3, ge=1, le=10)

    webhook_body_limit_bytes: int = Field(default=1_048_576, ge=1024)
    update_max_attempts: int = Field(default=3, ge=1, le=20)
    update_lease_seconds: int = Field(default=60, ge=10)
    state_conflict_retries: int = Field(default=5, ge=1, le=20)

    startup_db_max_attempts: int = Field(default=5, ge=1, le=30)
    startup_db_backoff_seconds: float = Field(default=1, gt=0, le=30)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def webhook_base_url(self) -> str:
        return str(self.public_base_url).rstrip("/")

    @property
    def credential_keys(self) -> list[SecretStr]:
        values = [
            value.strip()
            for value in self.bot_credential_keys.get_secret_value().split(",")
            if value.strip()
        ]
        if not values:
            raise ValueError("BOT_CREDENTIAL_KEYS must contain at least one key")
        return [SecretStr(value) for value in values]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
