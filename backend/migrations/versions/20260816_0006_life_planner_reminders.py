"""Create Life planner reminders and durable occurrences.

Revision ID: 20260816_0006
Revises: 20260816_0005
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_0006"
down_revision: str | None = "20260816_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "life_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination_id", sa.Integer(), sa.ForeignKey("life_notification_destinations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=1000)),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="reminder"),
        sa.Column("schedule_type", sa.String(length=16), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("recurrence", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_life_reminder_title"),
        sa.CheckConstraint("schedule_type IN ('one_time', 'recurring')", name="ck_life_reminder_schedule_type"),
        sa.CheckConstraint("kind IN ('reminder', 'routine', 'meal', 'workout')", name="ck_life_reminder_kind"),
    )
    op.create_index("ix_life_reminder_due", "life_reminders", ["enabled", "next_run_at"])
    op.create_index("ix_life_reminder_owner_due", "life_reminders", ["owner_user_id", "enabled", "next_run_at"])
    op.create_table(
        "life_reminder_occurrences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reminder_id", sa.Integer(), sa.ForeignKey("life_reminders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim_token", sa.String(length=64)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.String(length=64)),
        sa.Column("failure_detail", sa.String(length=255)),
        sa.Column("telegram_message_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("reminder_id", "scheduled_for", name="uq_life_occurrence_reminder_scheduled"),
        sa.CheckConstraint("status IN ('pending', 'claimed', 'sent', 'failed', 'missed', 'completed', 'skipped')", name="ck_life_occurrence_status"),
    )
    op.create_index("ix_life_occurrence_due", "life_reminder_occurrences", ["status", "available_at"])
    op.create_index("ix_life_occurrence_lease", "life_reminder_occurrences", ["status", "lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_life_occurrence_lease", table_name="life_reminder_occurrences")
    op.drop_index("ix_life_occurrence_due", table_name="life_reminder_occurrences")
    op.drop_table("life_reminder_occurrences")
    op.drop_index("ix_life_reminder_owner_due", table_name="life_reminders")
    op.drop_index("ix_life_reminder_due", table_name="life_reminders")
    op.drop_table("life_reminders")
