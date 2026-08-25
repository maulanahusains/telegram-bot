from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class GitlabInstanceModel(TimestampMixin, Base):
    __tablename__ = "gitlab_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabUserIdentityModel(TimestampMixin, Base):
    __tablename__ = "gitlab_user_identities"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", "instance_id", name="uq_gitlab_identity_user_instance"),
        Index("ix_gitlab_identity_status", "instance_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id", ondelete="CASCADE"), nullable=False)
    instance_id: Mapped[int] = mapped_column(ForeignKey("gitlab_instances.id", ondelete="RESTRICT"), nullable=False)
    external_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255))
    token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GitlabProjectModel(TimestampMixin, Base):
    __tablename__ = "gitlab_projects"
    __table_args__ = (
        UniqueConstraint("instance_id", "external_project_id", name="uq_gitlab_project_instance_external"),
        Index("ix_gitlab_project_active", "instance_id", "active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("gitlab_instances.id", ondelete="CASCADE"), nullable=False)
    external_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    namespace_path: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    web_url: Mapped[str | None] = mapped_column(String(1024))
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    service_credential_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_project_service_credentials.id", ondelete="SET NULL"))


class GitlabProjectServiceCredentialModel(TimestampMixin, Base):
    __tablename__ = "gitlab_project_service_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    identity_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_user_identities.id", ondelete="SET NULL"))
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    configured_by_bot_user_id: Mapped[int | None] = mapped_column(ForeignKey("bot_users.id", ondelete="SET NULL"))
    configured_by_external_user_id: Mapped[int | None] = mapped_column(BigInteger)


class GitlabProjectWebhookModel(TimestampMixin, Base):
    __tablename__ = "gitlab_project_webhooks"
    __table_args__ = (UniqueConstraint("project_id", name="uq_gitlab_webhook_project"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    external_webhook_id: Mapped[int | None] = mapped_column(BigInteger)
    route_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    signing_token_ciphertext: Mapped[str | None] = mapped_column(Text)
    trigger_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    sync_fingerprint: Mapped[str | None] = mapped_column(String(128))
    sync_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    last_failure: Mapped[str | None] = mapped_column(Text)


class GitlabProjectPermissionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_project_permissions"
    __table_args__ = (UniqueConstraint("project_id", "bot_user_id", "allowed_chat_id", name="uq_gitlab_project_permission_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    action_set: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    allowed_chat_id: Mapped[int | None] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabPromotionRuleModel(TimestampMixin, Base):
    __tablename__ = "gitlab_promotion_rules"
    __table_args__ = (UniqueConstraint("project_id", "display_name", name="uq_gitlab_promotion_rule_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    mr_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    successful_pipeline_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    manual_confirmation_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    production_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabPromotionRulePermissionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_promotion_rule_permissions"
    __table_args__ = (UniqueConstraint("rule_id", "bot_user_id", name="uq_gitlab_rule_permission_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("gitlab_promotion_rules.id", ondelete="CASCADE"), nullable=False)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabNotificationSubscriptionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_notification_subscriptions"
    __table_args__ = (UniqueConstraint("project_id", "telegram_chat_id", name="uq_gitlab_subscription_project_chat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False)
    event_categories: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    pipeline_mode: Mapped[str] = mapped_column(String(16), default="failures", nullable=False)
    branch_patterns: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabManualScriptMappingModel(TimestampMixin, Base):
    __tablename__ = "gitlab_manual_script_mappings"
    __table_args__ = (
        UniqueConstraint("project_id", "target_branch", "job_name", name="uq_gitlab_manual_script_mapping_job"),
        Index("ix_gitlab_manual_script_mapping_active", "project_id", "target_branch", "active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_label: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabManualScriptPermissionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_manual_script_permissions"
    __table_args__ = (UniqueConstraint("mapping_id", "bot_user_id", name="uq_gitlab_manual_script_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("gitlab_manual_script_mappings.id", ondelete="CASCADE"), nullable=False)
    bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class GitlabManualScriptRunModel(TimestampMixin, Base):
    __tablename__ = "gitlab_manual_script_runs"
    __table_args__ = (
        Index("ix_gitlab_manual_script_run_status", "project_id", "status"),
        Index("ix_gitlab_manual_script_run_external", "project_id", "pipeline_id", "job_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("gitlab_manual_script_mappings.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False)
    origin_message_id: Mapped[int | None] = mapped_column(Integer)
    pipeline_id: Mapped[int | None] = mapped_column(BigInteger)
    job_id: Mapped[int | None] = mapped_column(BigInteger)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(1024))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    actor_bot_user_id: Mapped[int | None] = mapped_column(ForeignKey("bot_users.id", ondelete="SET NULL"), nullable=True)


class GitlabAutomationAllowlistModel(TimestampMixin, Base):
    __tablename__ = "gitlab_automation_allowlist"
    __table_args__ = (UniqueConstraint("project_id", "external_author_id", name="uq_gitlab_automation_allowlist_author"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    external_author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))


class GitlabAutomationExecutionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_automation_executions"
    __table_args__ = (
        UniqueConstraint("project_id", "execution_key", name="uq_gitlab_automation_execution_key"),
        Index("ix_gitlab_automation_execution_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    mapping_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_manual_script_mappings.id", ondelete="SET NULL"))
    merge_request_iid: Mapped[int] = mapped_column(Integer, nullable=False)
    merge_request_sha: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    pipeline_id: Mapped[int | None] = mapped_column(BigInteger)
    job_id: Mapped[int | None] = mapped_column(BigInteger)
    error_summary: Mapped[str | None] = mapped_column(Text)


class GitlabWebhookInboxModel(TimestampMixin, Base):
    __tablename__ = "gitlab_webhook_inbox"
    __table_args__ = (
        UniqueConstraint("webhook_id", "delivery_key", name="uq_gitlab_inbox_delivery"),
        Index("ix_gitlab_inbox_processing", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("gitlab_project_webhooks.id", ondelete="CASCADE"), nullable=False)
    delivery_key: Mapped[str] = mapped_column(String(255), nullable=False)
    fallback_fingerprint: Mapped[str | None] = mapped_column(String(128), unique=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)


class GitlabNotificationMessageModel(TimestampMixin, Base):
    __tablename__ = "gitlab_notification_messages"
    __table_args__ = (UniqueConstraint("project_id", "telegram_chat_id", "resource_type", "external_resource_id", name="uq_gitlab_notification_resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_event_fingerprint: Mapped[str | None] = mapped_column(String(128))
    last_status: Mapped[str | None] = mapped_column(String(32))
    reply_markup: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class GitlabCallbackActionModel(TimestampMixin, Base):
    __tablename__ = "gitlab_callback_actions"
    __table_args__ = (Index("ix_gitlab_callback_action_expiry", "expires_at", "consumed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    action_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="CASCADE"))
    target: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    expected_sha: Mapped[str | None] = mapped_column(String(128))
    requester_bot_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GitlabAuditEventModel(Base):
    __tablename__ = "gitlab_audit_events"
    __table_args__ = (Index("ix_gitlab_audit_project_created", "project_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(ForeignKey("telegram_users.id", ondelete="SET NULL"))
    bot_user_id: Mapped[int | None] = mapped_column(ForeignKey("bot_users.id", ondelete="SET NULL"))
    identity_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_user_identities.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("gitlab_projects.id", ondelete="SET NULL"))
    merge_request_iid: Mapped[int | None] = mapped_column(Integer)
    merge_request_sha: Mapped[str | None] = mapped_column(String(128))
    pipeline_id: Mapped[int | None] = mapped_column(BigInteger)
    deployment_id: Mapped[int | None] = mapped_column(BigInteger)
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
