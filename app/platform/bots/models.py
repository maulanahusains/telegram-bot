from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class TelegramBotModel(TimestampMixin, Base):
    __tablename__ = "telegram_bots"
    __table_args__ = (Index("ix_telegram_bots_enabled", "enabled"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    secret_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(Text)
    webhook_sync_fingerprint: Mapped[str | None] = mapped_column(String(64))
    webhook_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

