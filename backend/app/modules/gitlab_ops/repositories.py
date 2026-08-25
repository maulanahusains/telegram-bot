from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gitlab_ops.models import (
    GitlabAuditEventModel,
    GitlabCallbackActionModel,
    GitlabInstanceModel,
    GitlabNotificationMessageModel,
    GitlabNotificationSubscriptionModel,
    GitlabManualScriptMappingModel,
    GitlabManualScriptPermissionModel,
    GitlabManualScriptRunModel,
    GitlabProjectModel,
    GitlabProjectPermissionModel,
    GitlabProjectWebhookModel,
    GitlabPromotionRuleModel,
    GitlabPromotionRulePermissionModel,
    GitlabUserIdentityModel,
    GitlabWebhookInboxModel,
)
from app.platform.users.models import BotUserModel, TelegramUserModel


class GitlabOpsRepository:
    async def get_instance(self, session: AsyncSession, base_url: str) -> GitlabInstanceModel | None:
        return await session.scalar(select(GitlabInstanceModel).where(GitlabInstanceModel.base_url == base_url))

    async def upsert_instance(self, session: AsyncSession, *, base_url: str, display_name: str) -> GitlabInstanceModel:
        model = await self.get_instance(session, base_url)
        if model is None:
            model = GitlabInstanceModel(base_url=base_url, display_name=display_name)
            session.add(model)
        else:
            model.display_name = display_name
            model.active = True
        await session.flush()
        return model

    async def identity(self, session: AsyncSession, *, telegram_user_id: int, instance_id: int) -> GitlabUserIdentityModel | None:
        return await session.scalar(select(GitlabUserIdentityModel).where(GitlabUserIdentityModel.telegram_user_id == telegram_user_id, GitlabUserIdentityModel.instance_id == instance_id))

    async def identities(self, session: AsyncSession, *, telegram_user_id: int) -> list[GitlabUserIdentityModel]:
        return list((await session.scalars(select(GitlabUserIdentityModel).where(GitlabUserIdentityModel.telegram_user_id == telegram_user_id).order_by(GitlabUserIdentityModel.id))).all())

    async def identity_for_instance(self, session: AsyncSession, *, telegram_user_id: int, instance_id: int, for_update: bool = False) -> GitlabUserIdentityModel | None:
        statement = select(GitlabUserIdentityModel).where(GitlabUserIdentityModel.telegram_user_id == telegram_user_id, GitlabUserIdentityModel.instance_id == instance_id, GitlabUserIdentityModel.status == "active")
        if for_update:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def save_identity(self, session: AsyncSession, *, telegram_user_id: int, instance_id: int, external_user_id: int, username: str | None, name: str | None, token_ciphertext: str) -> GitlabUserIdentityModel:
        model = await self.identity(session, telegram_user_id=telegram_user_id, instance_id=instance_id)
        if model is None:
            model = GitlabUserIdentityModel(telegram_user_id=telegram_user_id, instance_id=instance_id, external_user_id=external_user_id, username=username, name=name, token_ciphertext=token_ciphertext)
            session.add(model)
        else:
            model.external_user_id = external_user_id
            model.username = username
            model.name = name
            model.token_ciphertext = token_ciphertext
            model.status = "active"
        await session.flush()
        return model

    async def get_project(self, session: AsyncSession, project_id: int) -> GitlabProjectModel | None:
        return await session.get(GitlabProjectModel, project_id)

    async def get_project_by_external(self, session: AsyncSession, *, instance_id: int, external_project_id: int) -> GitlabProjectModel | None:
        return await session.scalar(select(GitlabProjectModel).where(GitlabProjectModel.instance_id == instance_id, GitlabProjectModel.external_project_id == external_project_id))

    async def save_project(self, session: AsyncSession, *, instance_id: int, external_project_id: int, namespace_path: str, name: str, web_url: str | None, default_branch: str) -> GitlabProjectModel:
        model = await self.get_project_by_external(session, instance_id=instance_id, external_project_id=external_project_id)
        if model is None:
            model = GitlabProjectModel(instance_id=instance_id, external_project_id=external_project_id, namespace_path=namespace_path, name=name, web_url=web_url, default_branch=default_branch)
            session.add(model)
        else:
            model.namespace_path = namespace_path
            model.name = name
            model.web_url = web_url
            model.default_branch = default_branch
            model.active = True
        await session.flush()
        return model

    async def projects_for_user(self, session: AsyncSession, *, bot_user_id: int, action: str | None = None, chat_row_id: int | None = None) -> list[GitlabProjectModel]:
        statement = select(GitlabProjectModel).join(GitlabProjectPermissionModel, GitlabProjectPermissionModel.project_id == GitlabProjectModel.id).where(GitlabProjectModel.active.is_(True), GitlabProjectPermissionModel.bot_user_id == bot_user_id, GitlabProjectPermissionModel.active.is_(True))
        if chat_row_id is not None:
            statement = statement.where(or_(GitlabProjectPermissionModel.allowed_chat_id.is_(None), GitlabProjectPermissionModel.allowed_chat_id == chat_row_id))
        if action is not None:
            statement = statement.where(GitlabProjectPermissionModel.action_set.contains([action]))
        statement = statement.distinct().order_by(GitlabProjectModel.namespace_path)
        return list((await session.scalars(statement)).all())

    async def get_webhook(self, session: AsyncSession, *, project_id: int) -> GitlabProjectWebhookModel | None:
        return await session.scalar(select(GitlabProjectWebhookModel).where(GitlabProjectWebhookModel.project_id == project_id))

    async def save_webhook(self, session: AsyncSession, *, project_id: int, route_key: str, secret_ciphertext: str, trigger_config: dict[str, bool], external_webhook_id: int | None, fingerprint: str) -> GitlabProjectWebhookModel:
        model = await self.get_webhook(session, project_id=project_id)
        if model is None:
            model = GitlabProjectWebhookModel(project_id=project_id, route_key=route_key, secret_ciphertext=secret_ciphertext, trigger_config=trigger_config, external_webhook_id=external_webhook_id, sync_fingerprint=fingerprint, sync_status="active")
            session.add(model)
        else:
            model.secret_ciphertext = secret_ciphertext
            model.external_webhook_id = external_webhook_id
            model.trigger_config = trigger_config
            model.sync_fingerprint = fingerprint
            model.sync_status = "active"
            model.last_failure = None
        await session.flush()
        return model

    async def permission(self, session: AsyncSession, *, project_id: int, bot_user_id: int, chat_row_id: int | None = None, action: str | None = None) -> GitlabProjectPermissionModel | None:
        statement = select(GitlabProjectPermissionModel).where(GitlabProjectPermissionModel.project_id == project_id, GitlabProjectPermissionModel.bot_user_id == bot_user_id, GitlabProjectPermissionModel.active.is_(True))
        if chat_row_id is not None:
            statement = statement.where(or_(GitlabProjectPermissionModel.allowed_chat_id.is_(None), GitlabProjectPermissionModel.allowed_chat_id == chat_row_id))
        models = list((await session.scalars(statement.order_by(GitlabProjectPermissionModel.allowed_chat_id.desc().nullslast()))).all())
        if action is None:
            return models[0] if models else None
        return next((model for model in models if action in model.action_set), None)

    async def save_permission(self, session: AsyncSession, *, project_id: int, bot_user_id: int, action_set: list[str], allowed_chat_id: int | None) -> GitlabProjectPermissionModel:
        statement = select(GitlabProjectPermissionModel).where(GitlabProjectPermissionModel.project_id == project_id, GitlabProjectPermissionModel.bot_user_id == bot_user_id, GitlabProjectPermissionModel.allowed_chat_id == allowed_chat_id)
        model = await session.scalar(statement)
        if model is None:
            model = GitlabProjectPermissionModel(project_id=project_id, bot_user_id=bot_user_id, action_set=action_set, allowed_chat_id=allowed_chat_id)
            session.add(model)
        else:
            model.action_set = action_set
            model.active = True
        await session.flush()
        return model

    async def rules(self, session: AsyncSession, *, project_id: int) -> list[GitlabPromotionRuleModel]:
        return list((await session.scalars(select(GitlabPromotionRuleModel).where(GitlabPromotionRuleModel.project_id == project_id, GitlabPromotionRuleModel.enabled.is_(True)).order_by(GitlabPromotionRuleModel.display_name))).all())

    async def rule(self, session: AsyncSession, *, project_id: int, display_name: str) -> GitlabPromotionRuleModel | None:
        return await session.scalar(select(GitlabPromotionRuleModel).where(GitlabPromotionRuleModel.project_id == project_id, GitlabPromotionRuleModel.display_name == display_name, GitlabPromotionRuleModel.enabled.is_(True)))

    async def save_rule(self, session: AsyncSession, *, project_id: int, values: dict[str, Any]) -> GitlabPromotionRuleModel:
        model = await self.rule(session, project_id=project_id, display_name=values["display_name"])
        if model is None:
            model = GitlabPromotionRuleModel(project_id=project_id, **values)
            session.add(model)
        else:
            for key, value in values.items():
                setattr(model, key, value)
        await session.flush()
        return model

    async def rule_permission(self, session: AsyncSession, *, rule_id: int, bot_user_id: int) -> GitlabPromotionRulePermissionModel | None:
        return await session.scalar(select(GitlabPromotionRulePermissionModel).where(GitlabPromotionRulePermissionModel.rule_id == rule_id, GitlabPromotionRulePermissionModel.bot_user_id == bot_user_id, GitlabPromotionRulePermissionModel.active.is_(True)))

    async def save_subscription(self, session: AsyncSession, *, project_id: int, telegram_chat_id: int, event_categories: list[str], pipeline_mode: str, branch_patterns: list[str]) -> GitlabNotificationSubscriptionModel:
        model = await session.scalar(select(GitlabNotificationSubscriptionModel).where(GitlabNotificationSubscriptionModel.project_id == project_id, GitlabNotificationSubscriptionModel.telegram_chat_id == telegram_chat_id))
        if model is None:
            model = GitlabNotificationSubscriptionModel(project_id=project_id, telegram_chat_id=telegram_chat_id, event_categories=event_categories, pipeline_mode=pipeline_mode, branch_patterns=branch_patterns)
            session.add(model)
        else:
            model.event_categories = event_categories
            model.pipeline_mode = pipeline_mode
            model.branch_patterns = branch_patterns
            model.enabled = True
        await session.flush()
        return model

    async def manual_mappings(self, session: AsyncSession, *, project_id: int, target_branch: str | None = None, bot_user_id: int | None = None) -> list[GitlabManualScriptMappingModel]:
        statement = select(GitlabManualScriptMappingModel).where(GitlabManualScriptMappingModel.project_id == project_id, GitlabManualScriptMappingModel.active.is_(True))
        if target_branch is not None:
            statement = statement.where(GitlabManualScriptMappingModel.target_branch == target_branch)
        if bot_user_id is not None:
            statement = statement.join(GitlabManualScriptPermissionModel, GitlabManualScriptPermissionModel.mapping_id == GitlabManualScriptMappingModel.id).where(GitlabManualScriptPermissionModel.bot_user_id == bot_user_id, GitlabManualScriptPermissionModel.active.is_(True))
        return list((await session.scalars(statement.order_by(GitlabManualScriptMappingModel.telegram_label))).all())

    async def manual_mapping(self, session: AsyncSession, mapping_id: int) -> GitlabManualScriptMappingModel | None:
        return await session.get(GitlabManualScriptMappingModel, mapping_id)

    async def save_manual_mapping(self, session: AsyncSession, *, project_id: int, target_branch: str, job_name: str, telegram_label: str) -> GitlabManualScriptMappingModel:
        model = await session.scalar(select(GitlabManualScriptMappingModel).where(GitlabManualScriptMappingModel.project_id == project_id, GitlabManualScriptMappingModel.target_branch == target_branch, GitlabManualScriptMappingModel.job_name == job_name))
        if model is None:
            model = GitlabManualScriptMappingModel(project_id=project_id, target_branch=target_branch, job_name=job_name, telegram_label=telegram_label)
            session.add(model)
        else:
            model.telegram_label = telegram_label
            model.active = True
        await session.flush()
        return model

    async def manual_permission(self, session: AsyncSession, *, mapping_id: int, bot_user_id: int) -> GitlabManualScriptPermissionModel | None:
        return await session.scalar(select(GitlabManualScriptPermissionModel).where(GitlabManualScriptPermissionModel.mapping_id == mapping_id, GitlabManualScriptPermissionModel.bot_user_id == bot_user_id, GitlabManualScriptPermissionModel.active.is_(True)))

    async def bot_user_by_telegram_id(self, session: AsyncSession, *, bot_id: int, telegram_user_id: int) -> BotUserModel | None:
        return await session.scalar(select(BotUserModel).join(TelegramUserModel, TelegramUserModel.id == BotUserModel.user_id).where(BotUserModel.bot_id == bot_id, TelegramUserModel.telegram_user_id == telegram_user_id))

    async def save_manual_permission(self, session: AsyncSession, *, mapping_id: int, bot_user_id: int) -> GitlabManualScriptPermissionModel:
        model = await session.scalar(select(GitlabManualScriptPermissionModel).where(GitlabManualScriptPermissionModel.mapping_id == mapping_id, GitlabManualScriptPermissionModel.bot_user_id == bot_user_id))
        if model is None:
            model = GitlabManualScriptPermissionModel(mapping_id=mapping_id, bot_user_id=bot_user_id)
            session.add(model)
        else:
            model.active = True
        await session.flush()
        return model

    async def add_manual_run(self, session: AsyncSession, *, mapping_id: int, project_id: int, telegram_chat_id: int, origin_message_id: int | None, ref: str, commit_sha: str, actor_bot_user_id: int) -> GitlabManualScriptRunModel:
        model = GitlabManualScriptRunModel(mapping_id=mapping_id, project_id=project_id, telegram_chat_id=telegram_chat_id, origin_message_id=origin_message_id, ref=ref, commit_sha=commit_sha, actor_bot_user_id=actor_bot_user_id, status="requested")
        session.add(model)
        await session.flush()
        return model

    async def manual_run(self, session: AsyncSession, run_id: int) -> GitlabManualScriptRunModel | None:
        return await session.get(GitlabManualScriptRunModel, run_id)

    async def manual_run_by_external(self, session: AsyncSession, *, project_id: int, pipeline_id: int | None = None, job_id: int | None = None) -> GitlabManualScriptRunModel | None:
        if pipeline_id is None and job_id is None:
            return None
        if pipeline_id is not None and job_id is not None:
            external_match = or_(
                GitlabManualScriptRunModel.job_id == job_id,
                and_(GitlabManualScriptRunModel.pipeline_id == pipeline_id, GitlabManualScriptRunModel.job_id.is_(None)),
            )
        else:
            external_match = GitlabManualScriptRunModel.pipeline_id == pipeline_id if pipeline_id is not None else GitlabManualScriptRunModel.job_id == job_id
        return await session.scalar(select(GitlabManualScriptRunModel).where(GitlabManualScriptRunModel.project_id == project_id, external_match).order_by(GitlabManualScriptRunModel.id.desc()))

    async def subscriptions(self, session: AsyncSession, *, project_id: int, category: str) -> list[GitlabNotificationSubscriptionModel]:
        statement = select(GitlabNotificationSubscriptionModel).where(GitlabNotificationSubscriptionModel.project_id == project_id, GitlabNotificationSubscriptionModel.enabled.is_(True))
        values = list((await session.scalars(statement)).all())
        return [value for value in values if category in value.event_categories]

    async def inbox_by_key(self, session: AsyncSession, *, webhook_id: int, delivery_key: str) -> GitlabWebhookInboxModel | None:
        return await session.scalar(select(GitlabWebhookInboxModel).where(GitlabWebhookInboxModel.webhook_id == webhook_id, GitlabWebhookInboxModel.delivery_key == delivery_key))

    async def pending_inbox(self, session: AsyncSession, *, now: datetime, limit: int) -> list[GitlabWebhookInboxModel]:
        statement = select(GitlabWebhookInboxModel).where(GitlabWebhookInboxModel.status == "pending", or_(GitlabWebhookInboxModel.next_attempt_at.is_(None), GitlabWebhookInboxModel.next_attempt_at <= now)).order_by(GitlabWebhookInboxModel.id).limit(limit).with_for_update(skip_locked=True)
        rows = list((await session.scalars(statement)).all())
        for row in rows:
            row.status = "processing"
            row.attempts += 1
        await session.flush()
        return rows

    async def notification(self, session: AsyncSession, *, project_id: int, chat_id: int, resource_type: str, external_resource_id: str) -> GitlabNotificationMessageModel | None:
        return await session.scalar(select(GitlabNotificationMessageModel).where(GitlabNotificationMessageModel.project_id == project_id, GitlabNotificationMessageModel.telegram_chat_id == chat_id, GitlabNotificationMessageModel.resource_type == resource_type, GitlabNotificationMessageModel.external_resource_id == external_resource_id))

    async def save_notification(self, session: AsyncSession, *, project_id: int, chat_id: int, resource_type: str, external_resource_id: str, message_id: int, fingerprint: str) -> GitlabNotificationMessageModel:
        model = await self.notification(session, project_id=project_id, chat_id=chat_id, resource_type=resource_type, external_resource_id=external_resource_id)
        if model is None:
            model = GitlabNotificationMessageModel(project_id=project_id, telegram_chat_id=chat_id, resource_type=resource_type, external_resource_id=external_resource_id, telegram_message_id=message_id, last_event_fingerprint=fingerprint)
            session.add(model)
        else:
            model.telegram_message_id = message_id
            model.last_event_fingerprint = fingerprint
        await session.flush()
        return model

    async def callback(self, session: AsyncSession, action_key: str) -> GitlabCallbackActionModel | None:
        return await session.scalar(select(GitlabCallbackActionModel).where(GitlabCallbackActionModel.action_key == action_key).with_for_update())

    async def audit(self, session: AsyncSession, **values: Any) -> GitlabAuditEventModel:
        model = GitlabAuditEventModel(**values)
        session.add(model)
        await session.flush()
        return model
