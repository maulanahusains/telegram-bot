"""Create platform application sessions.

Revision ID: 20260815_0004
Revises: 20260801_0003
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0004"
down_revision: str | None = "20260801_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("telegram_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "launching_bot_id",
            sa.Integer(),
            sa.ForeignKey("telegram_bots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint("token_hash", name="uq_application_sessions_token_hash"),
    )
    op.create_index(
        "ix_application_sessions_user_expires",
        "application_sessions",
        ["user_id", "expires_at"],
    )
    op.create_index(
        "ix_application_sessions_user_bot_active",
        "application_sessions",
        ["user_id", "launching_bot_id", "revoked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_sessions_user_bot_active", table_name="application_sessions"
    )
    op.drop_index(
        "ix_application_sessions_user_expires", table_name="application_sessions"
    )
    op.drop_table("application_sessions")
