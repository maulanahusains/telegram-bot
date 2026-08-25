"""Add GitLab Ops bot integration tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260823_0012"
down_revision: str | None = "20260823_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
json_type = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "gitlab_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("base_url", name="uq_gitlab_instances_base_url"),
    )
    op.create_table(
        "gitlab_user_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("gitlab_instances.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("name", sa.String(255)),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("telegram_user_id", "instance_id", name="uq_gitlab_identity_user_instance"),
    )
    op.create_index("ix_gitlab_identity_status", "gitlab_user_identities", ["instance_id", "status"])
    op.create_table(
        "gitlab_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("gitlab_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_project_id", sa.BigInteger(), nullable=False),
        sa.Column("namespace_path", sa.String(512), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("web_url", sa.String(1024)),
        sa.Column("default_branch", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("service_credential_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("instance_id", "external_project_id", name="uq_gitlab_project_instance_external"),
    )
    op.create_index("ix_gitlab_project_active", "gitlab_projects", ["instance_id", "active"])
    op.create_table(
        "gitlab_project_service_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_id", sa.Integer(), sa.ForeignKey("gitlab_user_identities.id", ondelete="SET NULL")),
        sa.Column("token_ciphertext", sa.Text()),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", name="uq_gitlab_project_service_credential_project"),
    )
    op.create_foreign_key("fk_gitlab_projects_service_credential", "gitlab_projects", "gitlab_project_service_credentials", ["service_credential_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "gitlab_project_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_webhook_id", sa.BigInteger()),
        sa.Column("route_key", sa.String(128), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("signing_token_ciphertext", sa.Text()),
        sa.Column("trigger_config", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sync_fingerprint", sa.String(128)),
        sa.Column("sync_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("last_failure", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", name="uq_gitlab_webhook_project"),
        sa.UniqueConstraint("route_key", name="uq_gitlab_webhook_route_key"),
    )
    op.create_table(
        "gitlab_project_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_set", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("allowed_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "bot_user_id", "allowed_chat_id", name="uq_gitlab_project_permission_scope"),
    )
    op.create_table(
        "gitlab_promotion_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("source_branch", sa.String(255), nullable=False),
        sa.Column("target_branch", sa.String(255), nullable=False),
        sa.Column("mr_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("successful_pipeline_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("manual_confirmation_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("production_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "display_name", name="uq_gitlab_promotion_rule_name"),
    )
    op.create_table(
        "gitlab_promotion_rule_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("gitlab_promotion_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("rule_id", "bot_user_id", name="uq_gitlab_rule_permission_user"),
    )
    op.create_table(
        "gitlab_notification_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_categories", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("pipeline_mode", sa.String(16), nullable=False, server_default="failures"),
        sa.Column("branch_patterns", json_type, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "telegram_chat_id", name="uq_gitlab_subscription_project_chat"),
    )
    op.create_table(
        "gitlab_webhook_inbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("gitlab_project_webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivery_key", sa.String(255), nullable=False),
        sa.Column("fallback_fingerprint", sa.String(128)),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("normalized_payload", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("error_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("webhook_id", "delivery_key", name="uq_gitlab_inbox_delivery"),
        sa.UniqueConstraint("fallback_fingerprint", name="uq_gitlab_inbox_fallback_fingerprint"),
    )
    op.create_index("ix_gitlab_inbox_processing", "gitlab_webhook_inbox", ["status", "next_attempt_at"])
    op.create_table(
        "gitlab_notification_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("external_resource_id", sa.String(255), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=False),
        sa.Column("last_event_fingerprint", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "telegram_chat_id", "resource_type", "external_resource_id", name="uq_gitlab_notification_resource"),
    )
    op.create_table(
        "gitlab_callback_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_key", sa.String(64), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="CASCADE")),
        sa.Column("target", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expected_sha", sa.String(128)),
        sa.Column("requester_bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("action_key", name="uq_gitlab_callback_action_key"),
    )
    op.create_index("ix_gitlab_callback_action_expiry", "gitlab_callback_actions", ["expires_at", "consumed_at"])
    op.create_table(
        "gitlab_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), sa.ForeignKey("telegram_users.id", ondelete="SET NULL")),
        sa.Column("bot_user_id", sa.Integer(), sa.ForeignKey("bot_users.id", ondelete="SET NULL")),
        sa.Column("identity_id", sa.Integer(), sa.ForeignKey("gitlab_user_identities.id", ondelete="SET NULL")),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("gitlab_projects.id", ondelete="SET NULL")),
        sa.Column("merge_request_iid", sa.Integer()),
        sa.Column("merge_request_sha", sa.String(128)),
        sa.Column("pipeline_id", sa.BigInteger()),
        sa.Column("deployment_id", sa.BigInteger()),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_gitlab_audit_project_created", "gitlab_audit_events", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_gitlab_audit_project_created", table_name="gitlab_audit_events")
    op.drop_table("gitlab_audit_events")
    op.drop_index("ix_gitlab_callback_action_expiry", table_name="gitlab_callback_actions")
    op.drop_table("gitlab_callback_actions")
    op.drop_table("gitlab_notification_messages")
    op.drop_index("ix_gitlab_inbox_processing", table_name="gitlab_webhook_inbox")
    op.drop_table("gitlab_webhook_inbox")
    op.drop_table("gitlab_notification_subscriptions")
    op.drop_table("gitlab_promotion_rule_permissions")
    op.drop_table("gitlab_promotion_rules")
    op.drop_table("gitlab_project_permissions")
    op.drop_table("gitlab_project_webhooks")
    op.drop_constraint("fk_gitlab_projects_service_credential", "gitlab_projects", type_="foreignkey")
    op.drop_table("gitlab_project_service_credentials")
    op.drop_index("ix_gitlab_project_active", table_name="gitlab_projects")
    op.drop_table("gitlab_projects")
    op.drop_index("ix_gitlab_identity_status", table_name="gitlab_user_identities")
    op.drop_table("gitlab_user_identities")
    op.drop_table("gitlab_instances")
