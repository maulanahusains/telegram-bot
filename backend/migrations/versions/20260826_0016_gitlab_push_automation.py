"""Add idempotent GitLab push automation runs."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0016"
down_revision: str | None = "20260826_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gitlab_automation_push_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ref", sa.String(255), nullable=False),
        sa.Column("commit_sha", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("pipeline_id", sa.BigInteger()),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "ref", "commit_sha", name="uq_gitlab_automation_push_run"),
    )
    op.create_index("ix_gitlab_automation_push_run_status", "gitlab_automation_push_runs", ["project_id", "status"])
    op.create_table(
        "gitlab_automation_push_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("gitlab_automation_push_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("gitlab_manual_script_mappings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pipeline_id", sa.BigInteger()),
        sa.Column("job_id", sa.BigInteger()),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "mapping_id", name="uq_gitlab_automation_push_execution_mapping"),
    )
    op.create_index("ix_gitlab_automation_push_execution_external", "gitlab_automation_push_executions", ["project_id", "pipeline_id", "job_id"])


def downgrade() -> None:
    op.drop_index("ix_gitlab_automation_push_execution_external", table_name="gitlab_automation_push_executions")
    op.drop_table("gitlab_automation_push_executions")
    op.drop_index("ix_gitlab_automation_push_run_status", table_name="gitlab_automation_push_runs")
    op.drop_table("gitlab_automation_push_runs")
