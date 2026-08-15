from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
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

    telegram_web_app_init_data_max_age_seconds: int = Field(
        default=300, ge=30, le=3600
    )
    telegram_web_app_clock_skew_seconds: int = Field(default=30, ge=0, le=300)
    application_session_ttl_seconds: int = Field(
        default=86_400, ge=300, le=2_592_000
    )
    application_session_cookie_name: str = Field(
        default="telegram_platform_session", min_length=1, max_length=128
    )
    application_session_cookie_secure: bool = True
    application_session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    life_reminder_executor_enabled: bool = False
    life_reminder_executor_interval_seconds: int = Field(default=30, ge=5, le=300)
    life_reminder_executor_batch_size: int = Field(default=50, ge=1, le=200)
    life_reminder_claim_lease_seconds: int = Field(default=120, ge=30, le=900)
    life_reminder_max_attempts: int = Field(default=3, ge=1, le=10)
    life_reminder_retry_base_seconds: int = Field(default=60, ge=5, le=3600)
    life_reminder_one_time_grace_seconds: int = Field(default=3600, ge=60, le=86_400)

    @model_validator(mode="after")
    def validate_session_cookie(self) -> Settings:
        if (
            self.application_session_cookie_samesite == "none"
            and not self.application_session_cookie_secure
        ):
            raise ValueError("SameSite=None session cookies must be Secure.")
        return self

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
