"""Add GitLab manual script runner tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0013"
down_revision: str | None = "20260823_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gitlab_manual_script_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_branch", sa.String(255), nullable=False),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("telegram_label", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "target_branch", "job_name", name="uq_gitlab_manual_script_mapping_job"),
    )
    op.create_index(
        "ix_gitlab_manual_script_mapping_active",
        "gitlab_manual_script_mappings",
        ["project_id", "target_branch", "active"],
    )
    op.create_table(
        "gitlab_manual_script_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("gitlab_manual_script_mappings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mapping_id", "bot_user_id", name="uq_gitlab_manual_script_permission"),
    )
    op.create_table(
        "gitlab_manual_script_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("gitlab_manual_script_mappings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin_message_id", sa.Integer()),
        sa.Column("pipeline_id", sa.BigInteger()),
        sa.Column("job_id", sa.BigInteger()),
        sa.Column("ref", sa.String(255), nullable=False),
        sa.Column("commit_sha", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("job_url", sa.String(1024)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("actor_bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_gitlab_manual_script_run_status", "gitlab_manual_script_runs", ["project_id", "status"])
    op.create_index("ix_gitlab_manual_script_run_external", "gitlab_manual_script_runs", ["project_id", "pipeline_id", "job_id"])


def downgrade() -> None:
    op.drop_index("ix_gitlab_manual_script_run_external", table_name="gitlab_manual_script_runs")
    op.drop_index("ix_gitlab_manual_script_run_status", table_name="gitlab_manual_script_runs")
    op.drop_table("gitlab_manual_script_runs")
    op.drop_table("gitlab_manual_script_permissions")
    op.drop_index("ix_gitlab_manual_script_mapping_active", table_name="gitlab_manual_script_mappings")
    op.drop_table("gitlab_manual_script_mappings")
