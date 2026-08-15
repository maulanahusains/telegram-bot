from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class ApplicationSessionModel(TimestampMixin, Base):
    __tablename__ = "application_sessions"
    __table_args__ = (
        Index("ix_application_sessions_user_expires", "user_id", "expires_at"),
        Index(
            "ix_application_sessions_user_bot_active",
            "user_id",
            "launching_bot_id",
            "revoked_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False
    )
    launching_bot_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_bots.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
