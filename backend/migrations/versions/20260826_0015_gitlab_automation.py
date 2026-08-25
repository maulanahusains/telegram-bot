"""Add GitLab automation configuration, allowlist, and idempotency records."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0015"
down_revision: str | None = "20260825_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gitlab_project_service_credentials", sa.Column("configured_by_bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="SET NULL")))
    op.add_column("gitlab_project_service_credentials", sa.Column("configured_by_external_user_id", sa.BigInteger()))
    op.create_table(
        "gitlab_automation_allowlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_author_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "external_author_id", name="uq_gitlab_automation_allowlist_author"),
    )
    op.create_table(
        "gitlab_automation_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("gitlab_manual_script_mappings.id", ondelete="SET NULL")),
        sa.Column("merge_request_iid", sa.Integer(), nullable=False),
        sa.Column("merge_request_sha", sa.String(128), nullable=False),
        sa.Column("execution_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("pipeline_id", sa.BigInteger()),
        sa.Column("job_id", sa.BigInteger()),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "execution_key", name="uq_gitlab_automation_execution_key"),
    )
    op.create_index("ix_gitlab_automation_execution_status", "gitlab_automation_executions", ["project_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_gitlab_automation_execution_status", table_name="gitlab_automation_executions")
    op.drop_table("gitlab_automation_executions")
    op.drop_table("gitlab_automation_allowlist")
    op.drop_column("gitlab_project_service_credentials", "configured_by_external_user_id")
    op.drop_column("gitlab_project_service_credentials", "configured_by_bot_user_id")
