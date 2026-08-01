"""Create Islamic bot tables.

Revision ID: 20260801_0003
Revises: 20260801_0002
Create Date: 2026-08-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0003"
down_revision: str | None = "20260801_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def upgrade() -> None:
    op.create_table(
        "islamic_scopes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id",
            sa.Integer(),
            sa.ForeignKey("telegram_bots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_type", sa.String(length=32), nullable=False),
        sa.Column("configured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("city", sa.String(length=128)),
        sa.Column("country", sa.String(length=128)),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Asia/Jakarta",
        ),
        sa.Column("calculation_method", sa.Integer()),
        sa.Column(
            "reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("active_reminder_message_id", sa.BigInteger()),
        sa.Column("setup_state", sa.String(length=64)),
        sa.Column(
            "setup_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_calendar_check_date", sa.Date()),
        *timestamps(),
        sa.UniqueConstraint("bot_id", "chat_id", name="uq_islamic_scope_bot_chat"),
    )
    op.create_index(
        "ix_islamic_scope_bot_configured",
        "islamic_scopes",
        ["bot_id", "configured"],
    )

    op.create_table(
        "islamic_prayer_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scope_id",
            sa.Integer(),
            sa.ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("prayer_name", sa.String(length=16), nullable=False),
        sa.Column("adhan_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quran_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pre_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("adhan_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("quran_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("claimed_kind", sa.String(length=16)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint(
            "scope_id", "local_date", "prayer_name", name="uq_prayer_scope_date_name"
        ),
    )
    op.create_index(
        "ix_prayer_due", "islamic_prayer_schedules", ["adhan_at", "quran_at"]
    )

    op.create_table(
        "islamic_quran_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scope_id",
            sa.Integer(),
            sa.ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_ayah_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_surah_number", sa.Integer()),
        sa.Column("last_surah_name", sa.String(length=128)),
        sa.Column("last_ayah_in_surah", sa.Integer()),
        sa.Column("last_page", sa.Integer()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("scope_id", name="uq_islamic_quran_progress_scope_id"),
    )

    op.create_table(
        "islamic_quran_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scope_id",
            sa.Integer(),
            sa.ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="idle"),
        sa.Column("mode", sa.String(length=16)),
        sa.Column("target_ayah_number", sa.Integer()),
        sa.Column(
            "current_batch",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("prompt_message_id", sa.BigInteger()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("scope_id", name="uq_islamic_quran_sessions_scope_id"),
    )
    op.create_index(
        "ix_quran_session_expiry",
        "islamic_quran_sessions",
        ["status", "expires_at"],
    )

    op.create_table(
        "islamic_quran_daily_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scope_id",
            sa.Integer(),
            sa.ForeignKey("islamic_scopes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("ayahs_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sessions_completed", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
        sa.UniqueConstraint("scope_id", "local_date", name="uq_quran_stat_scope_date"),
    )
    op.create_index(
        "ix_quran_stat_scope_date",
        "islamic_quran_daily_stats",
        ["scope_id", "local_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_quran_stat_scope_date", table_name="islamic_quran_daily_stats")
    op.drop_table("islamic_quran_daily_stats")
    op.drop_index("ix_quran_session_expiry", table_name="islamic_quran_sessions")
    op.drop_table("islamic_quran_sessions")
    op.drop_table("islamic_quran_progress")
    op.drop_index("ix_prayer_due", table_name="islamic_prayer_schedules")
    op.drop_table("islamic_prayer_schedules")
    op.drop_index("ix_islamic_scope_bot_configured", table_name="islamic_scopes")
    op.drop_table("islamic_scopes")
