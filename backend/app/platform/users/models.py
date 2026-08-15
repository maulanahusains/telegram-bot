from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class BotUserStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class TelegramUserModel(TimestampMixin, Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_bot: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TelegramChatModel(TimestampMixin, Base):
    __tablename__ = "telegram_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BotUserModel(TimestampMixin, Base):
    __tablename__ = "bot_users"
    __table_args__ = (
        UniqueConstraint("bot_id", "user_id", name="uq_bot_users_bot_id_user_id"),
        Index("ix_bot_users_bot_status", "bot_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BotUserStatus] = mapped_column(
        Enum(BotUserStatus, name="bot_user_status", values_callable=lambda e: [x.value for x in e]),
        default=BotUserStatus.ACTIVE,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    locale: Mapped[str | None] = mapped_column(String(16))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BotUserStateModel(TimestampMixin, Base):
    __tablename__ = "bot_user_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_user_id: Mapped[int] = mapped_column(
        ForeignKey("bot_users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    state: Mapped[str | None] = mapped_column(String(128))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

