"""Add GitLab notification lifecycle and callback retry state."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0014"
down_revision: str | None = "20260825_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("gitlab_notification_messages", sa.Column("last_status", sa.String(32)))
    op.add_column("gitlab_notification_messages", sa.Column("reply_markup", json_type))
    op.add_column("gitlab_callback_actions", sa.Column("processing_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("gitlab_callback_actions", "processing_at")
    op.drop_column("gitlab_notification_messages", "reply_markup")
    op.drop_column("gitlab_notification_messages", "last_status")
