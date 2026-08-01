from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UpdateStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class TelegramUpdateModel(Base):
    __tablename__ = "telegram_updates"
    __table_args__ = (
        UniqueConstraint("bot_id", "update_id", name="uq_telegram_updates_bot_update"),
        Index("ix_telegram_updates_status_lease", "status", "lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False
    )
    update_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    update_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[UpdateStatus] = mapped_column(
        Enum(UpdateStatus, name="telegram_update_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

