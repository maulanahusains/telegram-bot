from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from fnmatch import fnmatchcase
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.database import Database
from app.core.logging import get_logger
from app.core.telegram_client import SentMessage, TelegramBotClient
from app.modules.gitlab_ops.formatting import action_markup, branch_matches, deployment_text, mr_text, pipeline_text, push_text
from app.modules.gitlab_ops.gitlab_client import GitlabApiClient, normalize_gitlab_url
from app.modules.gitlab_ops.models import (
    GitlabCallbackActionModel,
    GitlabInstanceModel,
    GitlabManualScriptMappingModel,
    GitlabManualScriptPermissionModel,
    GitlabManualScriptRunModel,
    GitlabProjectModel,
    GitlabProjectPermissionModel,
    GitlabProjectWebhookModel,
    GitlabPromotionRulePermissionModel,
    GitlabPromotionRuleModel,
    GitlabUserIdentityModel,
    GitlabWebhookInboxModel,
)
from app.modules.gitlab_ops.repositories import GitlabOpsRepository
from app.modules.gitlab_ops.schemas import GitlabApiError, ManualScriptMappingInput, PromotionRuleInput, SubscriptionInput
from app.platform.bots.services import CredentialCipher
from app.platform.users.models import TelegramChatModel
from app.shared.types import ChatContext, UserContext
from app.shared.utils import safe_error_summary, utc_now

logger = get_logger(__name__)

ACTION_CREATE_MR = "create_merge_request"
ACTION_APPROVE_MR = "approve_merge_request"
ACTION_MERGE_MR = "merge_merge_request"
ACTION_INVOKE_PROMOTION = "invoke_promotion"
ACTION_INVOKE_PRODUCTION = "invoke_production_promotion"
ACTION_RUN_MANUAL_SCRIPT = "run_manual_script"
ACTION_CONFIRM_MANUAL_SCRIPT = "confirm_manual_script"
ACTION_APPROVE_AND_RUN = "approve_and_run"
ACTION_CONFIRM_APPROVE_AND_RUN = "confirm_approve_and_run"
ACTION_MANAGE_MANUAL_SCRIPTS = "manage_manual_scripts"
ACTION_VIEW_NOTIFICATIONS = "view_notifications"
ACTION_SELECTOR = "selector"

SELECTOR_DEPLOY = "deploy"
SELECTOR_BRANCHES = "branches"
SELECTOR_SCRIPTS = "scripts"
SELECTOR_RULE = "rule"
SELECTOR_SUBSCRIBE = "subscribe"
SELECTOR_SCRIPT_GRANT = "script_grant"
SELECTOR_PAGE_SIZE = 10


@dataclass(frozen=True, slots=True)
class CallbackReply:
    text: str | None
    reply_markup: dict[str, Any] | None = None
    edit_message_id: int | None = None
    next_state: str | None = None
    next_state_data: dict[str, Any] | None = None
    edit_markup_only: bool = False
    send_message: bool = True
    callback_text: str | None = None


@dataclass(frozen=True, slots=True)
class CallbackClaim:
    action: GitlabCallbackActionModel
    project: GitlabProjectModel
    instance: GitlabInstanceModel
    identity: GitlabUserIdentityModel
    edit_message_id: int | None
    original_reply_markup: dict[str, Any] | None


class GitlabOpsService:
    def __init__(self, *, database: Database, repository: GitlabOpsRepository, cipher: CredentialCipher, http: httpx.AsyncClient, settings: Settings, bot_id: int) -> None:
        self.database = database
        self.repository = repository
        self.cipher = cipher
        self.http = http
        self.settings = settings
        self.bot_id = bot_id

    async def identity_summary(self, context: UserContext) -> list[str]:
        async with self.database.session() as session:
            rows = await self.repository.identities(session, telegram_user_id=context.internal_user_id)
            instances = {row.instance_id: await session.get(GitlabInstanceModel, row.instance_id) for row in rows}
        return [f"{instances[row.instance_id].display_name if instances[row.instance_id] else 'GitLab'}: @{row.username or row.external_user_id} ({row.status})" for row in rows]

    async def connect_identity(self, context: UserContext, base_url: str, token: str) -> str:
        normalized = normalize_gitlab_url(base_url)
        client = GitlabApiClient(self.http, normalized, token)
        user = await client.current_user()
        async with self.database.transaction() as session:
            instance = await self.repository.upsert_instance(session, base_url=normalized, display_name=normalized.removeprefix("https://"))
            identity = await self.repository.save_identity(session, telegram_user_id=context.internal_user_id, instance_id=instance.id, external_user_id=user.external_user_id, username=user.username, name=user.name, token_ciphertext=self.cipher.encrypt(token))
            identity.last_validated_at = utc_now()
        return f"Terhubung sebagai <b>{_escape(user.name or user.username or str(user.external_user_id))}</b> di <code>{_escape(normalized)}</code>. Token tersimpan terenkripsi dan tidak ditampilkan ulang."

    async def selector_reply(self, context: UserContext, flow: str, *, page: int = 0) -> CallbackReply | str:
        async with self.database.transaction() as session:
            projects = await self._selector_projects(session, context, flow)
            if not projects:
                return self._empty_selector_text(flow)
            return await self._project_selector_markup(session, context, flow, projects, page)

    async def _selector_projects(self, session, context: UserContext, flow: str) -> list[GitlabProjectModel]:
        chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == context.chat_id))
        chat_id = chat.id if chat is not None else None
        if flow == SELECTOR_DEPLOY:
            return list({project.id: project for project, _ in await self._promotion_options(session, context, chat_id=chat_id)}.values())
        if flow in (SELECTOR_BRANCHES, SELECTOR_SCRIPTS, SELECTOR_SUBSCRIBE):
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS, chat_row_id=chat_id)
            return [project for project in projects if await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id) is not None]
        if flow == SELECTOR_RULE:
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id, action=ACTION_INVOKE_PROMOTION, chat_row_id=chat_id)
            return [project for project in projects if await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id) is not None]
        if flow == SELECTOR_SCRIPT_GRANT:
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
            return [project for project in projects if await self._can_manage_scripts(session, project.id, context.bot_user_id, chat_id=chat_id) and await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id) is not None and await self.repository.manual_mappings(session, project_id=project.id)]
        return []

    async def _promotion_options(self, session, context: UserContext, *, chat_id: int | None) -> list[tuple[GitlabProjectModel, GitlabPromotionRuleModel]]:
        projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
        options: list[tuple[GitlabProjectModel, GitlabPromotionRuleModel]] = []
        for project in projects:
            if await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id) is None:
                continue
            for rule in await self.repository.rules(session, project_id=project.id):
                action = ACTION_INVOKE_PRODUCTION if rule.production_sensitive else ACTION_INVOKE_PROMOTION
                if await self.repository.permission(session, project_id=project.id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=action) is None:
                    continue
                if await self.repository.rule_permission(session, rule_id=rule.id, bot_user_id=context.bot_user_id) is None:
                    continue
                options.append((project, rule))
        return options

    async def _can_manage_scripts(self, session, project_id: int, bot_user_id: int, *, chat_id: int | None) -> bool:
        return (
            await self.repository.permission(session, project_id=project_id, bot_user_id=bot_user_id, chat_row_id=chat_id, action=ACTION_MANAGE_MANUAL_SCRIPTS) is not None
            or await self.repository.permission(session, project_id=project_id, bot_user_id=bot_user_id, chat_row_id=chat_id, action=ACTION_INVOKE_PROMOTION) is not None
        )

    async def _project_selector_markup(self, session, context: UserContext, flow: str, projects: list[GitlabProjectModel], page: int) -> CallbackReply:
        page, total_pages = _page_bounds(len(projects), page)
        visible = projects[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]
        buttons: list[list[dict[str, str]]] = []
        for project in visible:
            key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project.id, target={"kind": "project", "flow": flow, "project_id": project.id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=await self._chat_row_id(session, context.chat_id))
            buttons.append([{"text": project.namespace_path, "callback_data": key}])
        navigation = await self._selector_navigation(session, context, flow, page, total_pages)
        if navigation:
            buttons.append(navigation)
        return CallbackReply(text=f"<b>Pilih project</b> untuk {selector_label(flow)} (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def _selector_navigation(self, session, context: UserContext, flow: str, page: int, total_pages: int, *, project_id: int | None = None) -> list[dict[str, str]]:
        if total_pages <= 1:
            return []
        row: list[dict[str, str]] = []
        chat_row_id = await self._chat_row_id(session, context.chat_id)
        if page > 0:
            key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "page", "flow": flow, "page": page - 1, "project_id": project_id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_row_id)
            row.append({"text": "⬅️ Sebelumnya", "callback_data": key})
        if page + 1 < total_pages:
            key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "page", "flow": flow, "page": page + 1, "project_id": project_id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_row_id)
            row.append({"text": "Berikutnya ➡️", "callback_data": key})
        return row

    async def _chat_row_id(self, session, telegram_chat_id: int) -> int:
        chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == telegram_chat_id))
        if chat is None:
            raise ValueError("Chat Telegram belum terdaftar.")
        return chat.id

    @staticmethod
    def _empty_selector_text(flow: str) -> str:
        if flow == SELECTOR_DEPLOY:
            return "Tidak ada project dengan promotion rule yang boleh kamu jalankan."
        if flow == SELECTOR_SCRIPT_GRANT:
            return "Tidak ada project manual script yang boleh kamu kelola."
        return f"Tidak ada project yang bisa kamu gunakan untuk {selector_label(flow)}."

    async def _selector_authorized(self, session, context: UserContext, target: dict[str, Any]) -> bool:
        flow = str(target.get("flow") or "")
        kind = str(target.get("kind") or "")
        project_id = _int_value(target.get("project_id"))
        if kind == "page" and project_id is None:
            return bool(await self._selector_projects(session, context, flow))
        if project_id is None:
            return False
        project = await self.repository.get_project(session, project_id)
        if project is None or not project.active:
            return False
        chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == context.chat_id))
        chat_id = chat.id if chat is not None else None
        if flow == SELECTOR_DEPLOY:
            if kind == "rule":
                rule = await session.get(GitlabPromotionRuleModel, _int_value(target.get("rule_id")) or 0)
                if rule is None or rule.project_id != project_id or not rule.enabled:
                    return False
                action = ACTION_INVOKE_PRODUCTION if rule.production_sensitive else ACTION_INVOKE_PROMOTION
                return await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=action) is not None and await self.repository.rule_permission(session, rule_id=rule.id, bot_user_id=context.bot_user_id) is not None
            return any(item_project.id == project_id for item_project, _ in await self._promotion_options(session, context, chat_id=chat_id))
        if flow in (SELECTOR_BRANCHES, SELECTOR_SCRIPTS):
            return await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=ACTION_VIEW_NOTIFICATIONS) is not None
        if flow == SELECTOR_RULE:
            return await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=ACTION_INVOKE_PROMOTION) is not None
        if flow == SELECTOR_SUBSCRIBE:
            return await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=ACTION_VIEW_NOTIFICATIONS) is not None
        if flow == SELECTOR_SCRIPT_GRANT:
            if not await self._can_manage_scripts(session, project_id, context.bot_user_id, chat_id=chat_id):
                return False
            if kind == "mapping":
                mapping = await self.repository.manual_mapping(session, _int_value(target.get("mapping_id")) or 0)
                return mapping is not None and mapping.project_id == project_id and mapping.active
            return True
        return False

    async def _handle_selector(self, context: UserContext, target: dict[str, Any], edit_message_id: int | None) -> CallbackReply | str:
        flow = str(target.get("flow") or "")
        kind = str(target.get("kind") or "")
        project_id = _int_value(target.get("project_id"))
        page = _int_value(target.get("page")) or 0
        if kind == "page":
            if project_id is None:
                reply = await self.selector_reply(context, flow, page=page)
            elif flow == SELECTOR_DEPLOY:
                reply = await self._rule_selector_reply(context, project_id, page=page)
            elif flow == SELECTOR_BRANCHES:
                reply = await self._branch_selector_reply(context, project_id, page=page)
            elif flow == SELECTOR_SCRIPTS:
                reply = await self._script_branch_selector_reply(context, project_id, page=page)
            elif flow == SELECTOR_SCRIPT_GRANT:
                reply = await self._mapping_selector_reply(context, project_id, page=page)
            else:
                reply = "Selector sudah tidak tersedia."
            return _with_edit_message(reply, edit_message_id)
        if kind == "project":
            if project_id is None:
                return "Project selector tidak valid."
            if flow == SELECTOR_DEPLOY:
                return _with_edit_message(await self._rule_selector_reply(context, project_id), edit_message_id)
            if flow == SELECTOR_BRANCHES:
                return _with_edit_message(await self._branch_selector_reply(context, project_id), edit_message_id)
            if flow == SELECTOR_SCRIPTS:
                return _with_edit_message(await self._script_branch_selector_reply(context, project_id), edit_message_id)
            if flow == SELECTOR_RULE:
                return CallbackReply(text="Kirim promotion rule dengan format `nama | source | target`.", edit_message_id=edit_message_id, next_state="gitlab_rule_input", next_state_data={"project_id": project_id, "chat_id": context.chat_id})
            if flow == SELECTOR_SUBSCRIBE:
                return CallbackReply(text="Kirim subscription dengan format `failures|all | branch1,release/*`.", edit_message_id=edit_message_id, next_state="gitlab_subscribe_input", next_state_data={"project_id": project_id, "chat_id": context.chat_id})
            if flow == SELECTOR_SCRIPT_GRANT:
                return _with_edit_message(await self._mapping_selector_reply(context, project_id), edit_message_id)
        if kind == "rule":
            rule_id = _int_value(target.get("rule_id"))
            if rule_id is None:
                return "Promotion rule tidak valid."
            async with self.database.session() as session:
                rule = await session.get(GitlabPromotionRuleModel, rule_id)
            if rule is None:
                return "Promotion rule sudah tidak aktif."
            prompt = await self.promotion_prompt(context, rule.project_id, rule.display_name)
            if prompt is not None:
                return CallbackReply(text=prompt[0], reply_markup=prompt[1], edit_message_id=edit_message_id)
            return CallbackReply(text=await self.deploy(context, rule.project_id, rule.display_name), edit_message_id=edit_message_id)
        if kind == "branch":
            return CallbackReply(text=f"Branch yang dipilih: <code>{_escape(str(target.get('branch') or ''))}</code>.", edit_message_id=edit_message_id)
        if kind == "script_branch":
            branch = str(target.get("branch") or "")
            try:
                reply = await self._job_selector_reply(
                    context,
                    project_id or 0,
                    branch,
                    page=page,
                )
            except GitlabApiError as error:
                if error.status_code == 422 and "pipeline did not run" in str(error).lower():
                    return CallbackReply(
                        text=(
                            "Workflow CI tidak dapat disimulasikan untuk branch "
                            f"<code>{_escape(branch)}</code>. Kirim nama job manualnya, "
                            "misalnya <code>deploy_development</code>."
                        ),
                        edit_message_id=edit_message_id,
                        next_state="gitlab_script_job_name",
                        next_state_data={
                            "project_id": project_id,
                            "target_branch": branch,
                            "chat_id": context.chat_id,
                            "manual_job_validation": "deferred",
                        },
                    )
                if error.status_code == 422:
                    return CallbackReply(
                        text=(
                            "<b>Konfigurasi CI tidak valid</b> untuk branch "
                            f"<code>{_escape(branch)}</code>:\n"
                            f"<code>{_escape(str(error)[:500])}</code>"
                        ),
                        edit_message_id=edit_message_id,
                    )
                return CallbackReply(
                    text=(
                        "Gagal membaca manual job dari GitLab "
                        f"(HTTP {error.status_code}): {_escape(str(error)[:400])}"
                    ),
                    edit_message_id=edit_message_id,
                )
            return _with_edit_message(reply, edit_message_id)
        if kind == "script_job":
            return CallbackReply(text="Kirim label Telegram untuk job ini, misalnya `Run Development`.", edit_message_id=edit_message_id, next_state="gitlab_script_label", next_state_data={"project_id": project_id, "target_branch": target.get("target_branch"), "job_name": target.get("job_name"), "chat_id": context.chat_id})
        if kind == "mapping":
            return CallbackReply(text="Kirim Telegram user ID target untuk mapping script ini.", edit_message_id=edit_message_id, next_state="gitlab_grant_user", next_state_data={"project_id": project_id, "mapping_id": target.get("mapping_id"), "chat_id": context.chat_id})
        return "Aksi selector tidak dikenali."

    async def _rule_selector_reply(self, context: UserContext, project_id: int, *, page: int = 0) -> CallbackReply | str:
        async with self.database.transaction() as session:
            chat_id = await self._chat_row_id(session, context.chat_id)
            project = await self.repository.get_project(session, project_id)
            if project is None or not project.active:
                return "Project tidak ditemukan atau sudah tidak aktif."
            options = []
            for rule in await self.repository.rules(session, project_id=project_id):
                action = ACTION_INVOKE_PRODUCTION if rule.production_sensitive else ACTION_INVOKE_PROMOTION
                if await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, chat_row_id=chat_id, action=action) is not None and await self.repository.rule_permission(session, rule_id=rule.id, bot_user_id=context.bot_user_id) is not None:
                    options.append(rule)
            if not options:
                return "Project ini tidak memiliki promotion rule yang boleh kamu jalankan."
            page, total_pages = _page_bounds(len(options), page)
            buttons = []
            for rule in options[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]:
                key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "rule", "flow": SELECTOR_DEPLOY, "project_id": project_id, "rule_id": rule.id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
                label = f"{rule.display_name} · {rule.source_branch} → {rule.target_branch}"
                buttons.append([{"text": label, "callback_data": key}])
            navigation = await self._selector_navigation(session, context, SELECTOR_DEPLOY, page, total_pages, project_id=project_id)
            if navigation:
                buttons.append(navigation)
            return CallbackReply(text=f"<b>Pilih promotion rule</b> untuk <code>{_escape(project.namespace_path)}</code> (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def _branch_selector_reply(self, context: UserContext, project_id: int, *, page: int = 0) -> CallbackReply | str:
        branches = await self.script_branch_options(context, project_id)
        if not branches:
            return "Tidak ada branch yang tersedia di project ini."
        async with self.database.transaction() as session:
            project = await self.repository.get_project(session, project_id)
            if project is None or not project.active:
                return "Project tidak ditemukan atau sudah tidak aktif."
            chat_id = await self._chat_row_id(session, context.chat_id)
            page, total_pages = _page_bounds(len(branches), page)
            buttons = []
            for branch in branches[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]:
                key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "branch", "flow": SELECTOR_BRANCHES, "project_id": project_id, "branch": branch["name"]}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
                label = str(branch["name"]) + (" · protected" if branch.get("protected") else "")
                buttons.append([{"text": label, "callback_data": key}])
            navigation = await self._selector_navigation(session, context, SELECTOR_BRANCHES, page, total_pages, project_id=project_id)
            if navigation:
                buttons.append(navigation)
            return CallbackReply(text=f"<b>Branches</b> · <code>{_escape(project.namespace_path)}</code> (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def _script_branch_selector_reply(self, context: UserContext, project_id: int, *, page: int = 0) -> CallbackReply | str:
        branches = await self.script_branch_options(context, project_id)
        if not branches:
            return "Tidak ada branch yang tersedia untuk manual script."
        async with self.database.transaction() as session:
            project = await self.repository.get_project(session, project_id)
            if project is None or not project.active:
                return "Project tidak ditemukan atau sudah tidak aktif."
            chat_id = await self._chat_row_id(session, context.chat_id)
            page, total_pages = _page_bounds(len(branches), page)
            buttons = []
            for branch in branches[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]:
                key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "script_branch", "flow": SELECTOR_SCRIPTS, "project_id": project_id, "branch": branch["name"]}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
                buttons.append([{"text": str(branch["name"]) + (" · protected" if branch.get("protected") else ""), "callback_data": key}])
            navigation = await self._selector_navigation(session, context, SELECTOR_SCRIPTS, page, total_pages, project_id=project_id)
            if navigation:
                buttons.append(navigation)
            return CallbackReply(text=f"<b>Pilih target branch untuk manual script</b> · <code>{_escape(project.namespace_path)}</code> (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def _job_selector_reply(self, context: UserContext, project_id: int, target_branch: str, *, page: int = 0) -> CallbackReply | str:
        jobs = await self.script_job_options(context, project_id, target_branch)
        jobs = [job for job in jobs if str(job.get("when") or "") == "manual"]
        if not jobs:
            return "Tidak ada job `when: manual` pada effective CI branch tersebut."
        async with self.database.transaction() as session:
            chat_id = await self._chat_row_id(session, context.chat_id)
            page, total_pages = _page_bounds(len(jobs), page)
            buttons = []
            for job in jobs[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]:
                key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "script_job", "flow": SELECTOR_SCRIPTS, "project_id": project_id, "target_branch": target_branch, "job_name": job.get("name")}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
                buttons.append([{"text": f"{job.get('name')} · stage={job.get('stage') or '-'}", "callback_data": key}])
            navigation = await self._selector_navigation(session, context, SELECTOR_SCRIPTS, page, total_pages, project_id=project_id)
            if navigation:
                buttons.append(navigation)
            return CallbackReply(text=f"<b>Pilih manual job</b> untuk <code>{_escape(target_branch)}</code> (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def _mapping_selector_reply(self, context: UserContext, project_id: int, *, page: int = 0) -> CallbackReply | str:
        async with self.database.transaction() as session:
            chat_id = await self._chat_row_id(session, context.chat_id)
            if not await self._can_manage_scripts(session, project_id, context.bot_user_id, chat_id=chat_id):
                return "Kamu tidak punya izin mengelola manual script project ini."
            mappings = await self.repository.manual_mappings(session, project_id=project_id)
            project = await self.repository.get_project(session, project_id)
            if project is None or not project.active:
                return "Project tidak ditemukan atau sudah tidak aktif."
            if not mappings:
                return "Belum ada manual script mapping di project ini."
            page, total_pages = _page_bounds(len(mappings), page)
            buttons = []
            for mapping in mappings[page * SELECTOR_PAGE_SIZE : (page + 1) * SELECTOR_PAGE_SIZE]:
                key = await self._create_callback_in_session(session, action_type=ACTION_SELECTOR, project_id=project_id, target={"kind": "mapping", "flow": SELECTOR_SCRIPT_GRANT, "project_id": project_id, "mapping_id": mapping.id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat_id)
                buttons.append([{"text": f"{mapping.telegram_label} · {mapping.target_branch} → {mapping.job_name}", "callback_data": key}])
            navigation = await self._selector_navigation(session, context, SELECTOR_SCRIPT_GRANT, page, total_pages, project_id=project_id)
            if navigation:
                buttons.append(navigation)
            return CallbackReply(text=f"<b>Pilih manual script</b> untuk <code>{_escape(project.namespace_path)}</code> (halaman {page + 1}/{total_pages}):", reply_markup={"inline_keyboard": buttons})

    async def discover_projects(self, context: UserContext) -> list[dict[str, Any]]:
        async with self.database.session() as session:
            identity = await self._identity_for_user(session, context.internal_user_id)
            if identity is None:
                return []
            instance = await session.get(GitlabInstanceModel, identity.instance_id)
        client = self._client(instance, identity)
        return [{**project.model_dump(), "instance_id": identity.instance_id} async for project in client.projects()]

    async def setup_project(self, context: UserContext, project_data: dict[str, Any]) -> str:
        async with self.database.transaction() as session:
            identity = await self._identity_for_user(session, context.internal_user_id, for_update=True, instance_id=int(project_data["instance_id"]))
            if identity is None:
                raise ValueError("Hubungkan GitLab dulu dengan /gitlab.")
            instance = await session.get(GitlabInstanceModel, identity.instance_id)
            if instance is None:
                raise ValueError("GitLab instance tidak ditemukan.")
            project = await self.repository.save_project(session, instance_id=instance.id, external_project_id=int(project_data["id"]), namespace_path=str(project_data["path_with_namespace"]), name=str(project_data["name"]), web_url=project_data.get("web_url"), default_branch=str(project_data.get("default_branch") or "main"))
            await self.repository.save_permission(session, project_id=project.id, bot_user_id=context.bot_user_id, action_set=["view_notifications", ACTION_CREATE_MR, ACTION_APPROVE_MR, ACTION_MERGE_MR, ACTION_INVOKE_PROMOTION, ACTION_INVOKE_PRODUCTION, ACTION_MANAGE_MANUAL_SCRIPTS], allowed_chat_id=None)
            route_key = secrets.token_urlsafe(24)
            secret = secrets.token_urlsafe(32)
            trigger = {"push_events": True, "merge_requests_events": True, "pipeline_events": True, "deployment_events": True, "job_events": True}
            webhook = await self.repository.get_webhook(session, project_id=project.id)
            if webhook is None:
                webhook = GitlabProjectWebhookModel(project_id=project.id, route_key=route_key, secret_ciphertext=self.cipher.encrypt(secret), trigger_config=trigger)
                session.add(webhook)
                await session.flush()
            else:
                route_key = webhook.route_key
                secret = self.cipher.decrypt(webhook.secret_ciphertext).get_secret_value()
            client = self._client(instance, identity)
            hook_url = f"{self.settings.webhook_base_url}/webhooks/gitlab/{route_key}"
            try:
                remote = await self._reconcile_hook(client, project.external_project_id, webhook, hook_url, secret, trigger)
                webhook.external_webhook_id = int(remote["id"])
                webhook.sync_status = "active"
                webhook.last_failure = None
                webhook.sync_fingerprint = _fingerprint(json.dumps({"url": hook_url, **trigger}, sort_keys=True))
            except GitlabApiError as error:
                webhook.sync_status = "degraded"
                webhook.last_failure = f"HTTP {error.status_code}: {str(error)[:400]}"
                return f"Project <b>{_escape(project.namespace_path)}</b> tersimpan, tetapi webhook gagal disiapkan (GitLab HTTP {error.status_code}). Periksa token admin project lalu ulangi setup."
            return f"Project <b>{_escape(project.namespace_path)}</b> aktif. Webhook: <code>{_escape(webhook.sync_status)}</code>. Gunakan /projects untuk melihat status."

    async def save_rule(self, context: UserContext, project_id: int, values: PromotionRuleInput) -> str:
        async with self.database.transaction() as session:
            if await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_INVOKE_PROMOTION) is None:
                raise PermissionError("Kamu tidak punya izin mengelola promotion rule project ini.")
            rule = await self.repository.save_rule(session, project_id=project_id, values=values.model_dump())
            permission = await session.scalar(select(GitlabPromotionRulePermissionModel).where(GitlabPromotionRulePermissionModel.rule_id == rule.id, GitlabPromotionRulePermissionModel.bot_user_id == context.bot_user_id))
            if permission is None:
                session.add(GitlabPromotionRulePermissionModel(rule_id=rule.id, bot_user_id=context.bot_user_id))
        return f"Promotion rule <b>{_escape(values.display_name)}</b> tersimpan: <code>{_escape(values.source_branch)} → {_escape(values.target_branch)}</code>."

    async def save_subscription(self, context: UserContext, project_id: int, values: SubscriptionInput) -> str:
        async with self.database.transaction() as session:
            if await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS) is None:
                raise PermissionError("Kamu tidak punya izin melihat notifikasi project ini.")
            chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == context.chat_id))
            if chat is None:
                raise ValueError("Chat Telegram belum terdaftar.")
            await self.repository.save_subscription(session, project_id=project_id, telegram_chat_id=chat.id, event_categories=values.event_categories, pipeline_mode=values.pipeline_mode, branch_patterns=values.branch_patterns)
        return "Subscription project aktif di chat ini."

    async def list_projects_text(self, context: UserContext) -> str:
        async with self.database.session() as session:
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS)
            if not projects:
                return "Belum ada project terdaftar. Hubungkan GitLab lalu pilih project lewat /gitlab."
            lines = ["<b>Project yang bisa kamu lihat</b>"]
            for project in projects:
                webhook = await self.repository.get_webhook(session, project_id=project.id)
                rules = await self.repository.rules(session, project_id=project.id)
                mappings = await self.repository.manual_mappings(session, project_id=project.id)
                lines.append(f"<b>{_escape(project.namespace_path)}</b> · webhook={_escape(webhook.sync_status if webhook else 'belum diatur')} · rules={len(rules)} · mappings={len(mappings)}")
            return "\n".join(lines)

    async def show_branches(self, context: UserContext, project_id: int) -> str:
        async with self.database.session() as session:
            project = await self.repository.get_project(session, project_id)
            if project is None or await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS) is None:
                raise PermissionError("Project tidak ditemukan atau kamu tidak punya akses.")
            identity = await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id)
            instance = await session.get(GitlabInstanceModel, project.instance_id)
        if identity is None or instance is None:
            raise ValueError("Identity GitLab untuk instance project tidak tersedia.")
        branches = await self._client(instance, identity).branches(project.external_project_id)
        return "<b>Branches</b>\n" + "\n".join(f"• <code>{_escape(branch.name)}</code>{' · protected' if branch.protected else ''}" for branch in branches[:100])

    async def script_branch_options(self, context: UserContext, project_id: int) -> list[dict[str, Any]]:
        async with self.database.session() as session:
            project = await self.repository.get_project(session, project_id)
            if project is None or await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS) is None:
                raise PermissionError("Project tidak ditemukan atau kamu tidak punya akses.")
            identity = await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id)
            instance = await session.get(GitlabInstanceModel, project.instance_id)
        if identity is None or instance is None:
            raise ValueError("Identity GitLab untuk instance project tidak tersedia.")
        return [branch.model_dump() for branch in await self._client(instance, identity).branches(project.external_project_id)]

    async def script_job_options(self, context: UserContext, project_id: int, target_branch: str) -> list[dict[str, Any]]:
        async with self.database.session() as session:
            project = await self.repository.get_project(session, project_id)
            if project is None or await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_VIEW_NOTIFICATIONS) is None:
                raise PermissionError("Project tidak ditemukan atau kamu tidak punya akses.")
            identity = await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id)
            instance = await session.get(GitlabInstanceModel, project.instance_id)
        if identity is None or instance is None:
            raise ValueError("Identity GitLab untuk instance project tidak tersedia.")
        return await self._client(instance, identity).effective_manual_jobs(project.external_project_id, ref=target_branch)

    async def save_script_mapping(
        self,
        context: UserContext,
        project_id: int,
        values: ManualScriptMappingInput,
        *,
        validate_job: bool = True,
    ) -> str:
        async with self.database.session() as session:
            if await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_MANAGE_MANUAL_SCRIPTS) is None and await self.repository.permission(session, project_id=project_id, bot_user_id=context.bot_user_id, action=ACTION_INVOKE_PROMOTION) is None:
                raise PermissionError("Kamu tidak punya izin mengelola manual script project ini.")
        if validate_job:
            jobs = await self.script_job_options(context, project_id, values.target_branch)
            selected = next((job for job in jobs if job.get("name") == values.job_name and job.get("when") == "manual"), None)
            if selected is None:
                raise ValueError("Job tidak ditemukan sebagai job manual pada effective CI branch tersebut.")
        async with self.database.transaction() as session:
            mapping = await self.repository.save_manual_mapping(session, project_id=project_id, target_branch=values.target_branch, job_name=values.job_name, telegram_label=values.telegram_label)
            await self.repository.save_manual_permission(session, mapping_id=mapping.id, bot_user_id=context.bot_user_id)
        return f"Manual script <b>{_escape(values.telegram_label)}</b> tersimpan untuk <code>{_escape(values.target_branch)}</code> → <code>{_escape(values.job_name)}</code>. Izin awal diberikan ke kamu."

    async def script_mappings_text(self, context: UserContext, project_id: int) -> str:
        async with self.database.session() as session:
            mappings = await self.repository.manual_mappings(session, project_id=project_id)
        if not mappings:
            return "Belum ada manual script mapping untuk project ini. Gunakan /gitlab scripts untuk memilih project."
        return "<b>Manual scripts</b>\n" + "\n".join(f"{_escape(mapping.telegram_label)} · <code>{_escape(mapping.target_branch)}</code> → <code>{_escape(mapping.job_name)}</code>" for mapping in mappings)

    async def grant_script_permission(self, context: UserContext, mapping_id: int, telegram_user_id: int) -> str:
        async with self.database.transaction() as session:
            mapping = await self.repository.manual_mapping(session, mapping_id)
            if mapping is None or not mapping.active:
                raise ValueError("Manual script mapping tidak ditemukan.")
            if await self.repository.permission(session, project_id=mapping.project_id, bot_user_id=context.bot_user_id, action=ACTION_MANAGE_MANUAL_SCRIPTS) is None and await self.repository.permission(session, project_id=mapping.project_id, bot_user_id=context.bot_user_id, action=ACTION_INVOKE_PROMOTION) is None:
                raise PermissionError("Kamu tidak punya izin mengelola permission project ini.")
            target_user = await self.repository.bot_user_by_telegram_id(session, bot_id=self.bot_id, telegram_user_id=telegram_user_id)
            if target_user is None:
                raise ValueError("User target belum pernah berinteraksi dengan bot ini.")
            await self.repository.save_manual_permission(session, mapping_id=mapping.id, bot_user_id=target_user.id)
        return f"Izin manual script <b>{_escape(mapping.telegram_label)}</b> diberikan ke Telegram user <code>{telegram_user_id}</code>."

    async def deploy(self, context: UserContext, project_id: int, rule_name: str) -> str:
        async with self.database.session() as session:
            project = await self.repository.get_project(session, project_id)
            rule = await self.repository.rule(session, project_id=project_id, display_name=rule_name)
            if project is None or rule is None:
                raise ValueError("Project, promotion rule, atau koneksi GitLab tidak ditemukan.")
            identity = await self._identity_for_user(session, context.internal_user_id, instance_id=project.instance_id)
            if identity is None:
                raise ValueError("Project, promotion rule, atau koneksi GitLab tidak ditemukan.")
            permission = await self.repository.permission(session, project_id=project.id, bot_user_id=context.bot_user_id, action=ACTION_INVOKE_PRODUCTION if rule.production_sensitive else ACTION_INVOKE_PROMOTION)
            rule_permission = await self.repository.rule_permission(session, rule_id=rule.id, bot_user_id=context.bot_user_id)
            instance = await session.get(GitlabInstanceModel, project.instance_id)
            if permission is None or rule_permission is None or instance is None:
                raise PermissionError("Kamu tidak diizinkan menjalankan promotion rule ini.")
        client = self._client(instance, identity)
        open_mrs = await client.merge_requests(project.external_project_id, source_branch=rule.source_branch, target_branch=rule.target_branch)
        if open_mrs:
            mr = open_mrs[0]
            return f"MR yang sama sudah terbuka: !{mr.iid} <a href=\"{_escape(str(mr.web_url or ''), quote=True)}\">lihat di GitLab</a>. Bot tidak membuat duplikat."
        if not rule.mr_required:
            return "Promotion rule ini dikonfigurasi tanpa MR; eksekusi langsung belum diaktifkan di MVP."
        mr = await client.create_merge_request(project.external_project_id, source_branch=rule.source_branch, target_branch=rule.target_branch, title=f"Promote {rule.source_branch} to {rule.target_branch}")
        await self._audit(context, project.id, "promotion_create_merge_request", "success", identity_id=identity.id, merge_request_iid=mr.iid, merge_request_sha=mr.sha)
        return f"MR !{mr.iid} dibuat untuk <code>{_escape(rule.source_branch)} → {_escape(rule.target_branch)}</code>. GitLab tetap menjadi authority untuk approval, pipeline, dan merge."

    async def promotion_prompt(self, context: UserContext, project_id: int, rule_name: str) -> tuple[str, dict[str, Any]] | None:
        async with self.database.session() as session:
            project = await self.repository.get_project(session, project_id)
            rule = await self.repository.rule(session, project_id=project_id, display_name=rule_name)
            chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == context.chat_id))
            if project is None or rule is None or chat is None:
                raise ValueError("Project, promotion rule, atau chat tidak ditemukan.")
            action = ACTION_INVOKE_PRODUCTION if rule.production_sensitive else ACTION_INVOKE_PROMOTION
            if await self.repository.permission(session, project_id=project.id, bot_user_id=context.bot_user_id, action=action, chat_row_id=chat.id) is None or await self.repository.rule_permission(session, rule_id=rule.id, bot_user_id=context.bot_user_id) is None:
                raise PermissionError("Kamu tidak diizinkan menjalankan promotion rule ini.")
            if not rule.manual_confirmation_required:
                return None
        key = await self.create_callback(action_type=action, project_id=project_id, target={"rule_id": rule.id}, expected_sha=None, bot_user_id=context.bot_user_id, chat_row_id=chat.id)
        return (
            f"Konfirmasi promotion <b>{_escape(rule.display_name)}</b>: <code>{_escape(rule.source_branch)} → {_escape(rule.target_branch)}</code>.",
            action_markup([("Konfirmasi promotion", key)]) or {},
        )

    async def show_mrs(self, context: UserContext) -> str:
        async with self.database.session() as session:
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id)
            identities = await self.repository.identities(session, telegram_user_id=context.internal_user_id)
            identities_by_instance = {identity.instance_id: identity for identity in identities}
            instances = {project.instance_id: await session.get(GitlabInstanceModel, project.instance_id) for project in projects}
        if not identities_by_instance:
            return "Hubungkan GitLab dulu dengan /gitlab."
        lines = ["<b>Merge request relevan</b>"]
        for project in projects[:10]:
            instance = instances.get(project.instance_id)
            if instance is None:
                continue
            identity = identities_by_instance.get(project.instance_id)
            if identity is None:
                continue
            for mr in await self._client(instance, identity).merge_requests(project.external_project_id):
                lines.append(f"{_escape(project.namespace_path)} · !{mr.iid} · <code>{_escape(mr.state)}</code> · {_escape(mr.source_branch)} → {_escape(mr.target_branch)}")
        return "\n".join(lines) if len(lines) > 1 else "Tidak ada MR terbuka di project yang bisa kamu lihat."

    async def show_pipelines(self, context: UserContext) -> str:
        async with self.database.session() as session:
            projects = await self.repository.projects_for_user(session, bot_user_id=context.bot_user_id)
            identities = await self.repository.identities(session, telegram_user_id=context.internal_user_id)
            identities_by_instance = {identity.instance_id: identity for identity in identities}
            instances = {project.instance_id: await session.get(GitlabInstanceModel, project.instance_id) for project in projects}
        if not identities_by_instance:
            return "Hubungkan GitLab dulu dengan /gitlab."
        lines = ["<b>Pipeline terbaru</b>"]
        for project in projects[:10]:
            instance = instances.get(project.instance_id)
            if instance is None:
                continue
            identity = identities_by_instance.get(project.instance_id)
            if identity is None:
                continue
            for pipeline in (await self._client(instance, identity).pipelines(project.external_project_id))[:5]:
                lines.append(f"{_escape(project.namespace_path)} · #{pipeline.id} · <code>{_escape(str(pipeline.status or 'unknown'))}</code> · {_escape(str(pipeline.ref or ''))}")
        return "\n".join(lines) if len(lines) > 1 else "Belum ada pipeline yang bisa ditampilkan."

    async def ingest_webhook(self, *, route_key: str, headers: dict[str, str], raw_body: bytes) -> bool:
        async with self.database.transaction() as session:
            webhook = await session.scalar(select(GitlabProjectWebhookModel).where(GitlabProjectWebhookModel.route_key == route_key).with_for_update())
            if webhook is None or not self._verify_webhook(webhook, headers, raw_body):
                return False
            try:
                payload = json.loads(raw_body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                return False
            project_data = payload.get("project") if isinstance(payload, dict) else None
            project = await session.get(GitlabProjectModel, webhook.project_id)
            if not isinstance(project_data, dict) or project_data.get("id") is None or project is None:
                return False
            if int(project_data["id"]) != project.external_project_id:
                return False
            event_type = headers.get("x-gitlab-event", "unknown").lower().replace(" ", "_")
            delivery_key = headers.get("x-gitlab-webhook-uuid") or headers.get("idempotency-key") or _fingerprint(f"{webhook.project_id}:{event_type}:{hashlib.sha256(raw_body).hexdigest()}")
            existing = await self.repository.inbox_by_key(session, webhook_id=webhook.id, delivery_key=delivery_key)
            if existing is not None:
                return True
            row = GitlabWebhookInboxModel(webhook_id=webhook.id, delivery_key=delivery_key, fallback_fingerprint=delivery_key if not headers.get("x-gitlab-webhook-uuid") and not headers.get("idempotency-key") else None, event_type=event_type, normalized_payload=_sanitize_payload(payload))
            try:
                async with session.begin_nested():
                    session.add(row)
                    await session.flush()
            except IntegrityError:
                return True
            return True

    async def process_pending(self, telegram: TelegramBotClient, *, batch_size: int) -> None:
        async with self.database.transaction() as session:
            rows = await self.repository.pending_inbox(session, now=utc_now(), limit=batch_size)
        for row in rows:
            try:
                await self._process_event(telegram, row)
                async with self.database.transaction() as session:
                    current = await session.get(GitlabWebhookInboxModel, row.id, with_for_update=True)
                    if current:
                        current.status = "processed"
                        current.processed_at = utc_now()
            except Exception as error:
                async with self.database.transaction() as session:
                    current = await session.get(GitlabWebhookInboxModel, row.id, with_for_update=True)
                    if current:
                        current.status = "pending" if current.attempts < 5 else "failed"
                        current.next_attempt_at = utc_now() + timedelta(seconds=min(300, 2 ** current.attempts * 5))
                        current.error_summary = safe_error_summary(error)
                await logger.aexception("gitlab_event_processing_failed", inbox_id=row.id, error_type=type(error).__name__)

    async def create_callback(self, *, action_type: str, project_id: int | None, target: dict[str, Any], expected_sha: str | None, bot_user_id: int, chat_row_id: int) -> str:
        key = secrets.token_urlsafe(12)
        async with self.database.transaction() as session:
            session.add(GitlabCallbackActionModel(action_key=key, action_type=action_type, project_id=project_id, target=target, expected_sha=expected_sha, requester_bot_user_id=bot_user_id, chat_id=chat_row_id, expires_at=utc_now() + timedelta(minutes=15)))
        return f"glo:v1:{key}"

    async def claim_callback(self, context: UserContext, callback_data: str, *, edit_message_id: int | None = None) -> str | CallbackReply | CallbackClaim:
        if not callback_data.startswith("glo:v1:"):
            return "Aksi tidak dikenali."
        key = callback_data.removeprefix("glo:v1:")
        claim: CallbackClaim | None = None
        async with self.database.transaction() as session:
            action = await self.repository.callback(session, key)
            now = utc_now()
            if action is None or action.consumed_at is not None or action.expires_at <= now:
                return "Aksi sudah kedaluwarsa atau sudah dipakai."
            if action.requester_bot_user_id != context.bot_user_id:
                return "Aksi ini bukan milik requester tersebut."
            chat = await session.scalar(select(TelegramChatModel).where(TelegramChatModel.telegram_chat_id == context.chat_id))
            if chat is None or chat.id != action.chat_id:
                return "Aksi ini terikat ke chat lain."
            if action.action_type == ACTION_SELECTOR:
                selector_target = dict(action.target)
                if not await self._selector_authorized(session, context, selector_target):
                    await self.repository.audit(session, action="callback:selector", result="denied", bot_user_id=context.bot_user_id, project_id=action.project_id, metadata_={"reason": "permission"})
                    return "Project atau resource selector sudah tidak diizinkan."
                action.consumed_at = utc_now()
                project = None
                identity = None
                instance = None
            else:
                selector_target = None
                project = await self.repository.get_project(session, action.project_id or 0)
                if project is None:
                    return "Project aksi tidak ditemukan."
                identity = await self._identity_for_user(session, context.internal_user_id, for_update=True, instance_id=project.instance_id)
                if identity is None:
                    return "Koneksi GitLab tidak tersedia. Gunakan /gitlab untuk reconnect."
                runner_action = action.action_type in (ACTION_RUN_MANUAL_SCRIPT, ACTION_CONFIRM_MANUAL_SCRIPT, ACTION_APPROVE_AND_RUN, ACTION_CONFIRM_APPROVE_AND_RUN)
                project_action = ACTION_APPROVE_MR if action.action_type in (ACTION_APPROVE_AND_RUN, ACTION_CONFIRM_APPROVE_AND_RUN) else ACTION_VIEW_NOTIFICATIONS if runner_action else action.action_type
                permission = await self.repository.permission(session, project_id=project.id, bot_user_id=context.bot_user_id, action=project_action, chat_row_id=chat.id)
                instance = await session.get(GitlabInstanceModel, project.instance_id)
                if action.action_type in (ACTION_INVOKE_PROMOTION, ACTION_INVOKE_PRODUCTION):
                    rule_id = action.target.get("rule_id")
                    if not rule_id or await self.repository.rule_permission(session, rule_id=int(rule_id), bot_user_id=context.bot_user_id) is None:
                        permission = None
                if runner_action:
                    mapping_id = action.target.get("mapping_id")
                    mapping = await self.repository.manual_mapping(session, int(mapping_id)) if mapping_id else None
                    if mapping is None or mapping.project_id != project.id or not mapping.active or await self.repository.manual_permission(session, mapping_id=mapping.id, bot_user_id=context.bot_user_id) is None:
                        permission = None
                if permission is None or instance is None:
                    await self.repository.audit(session, action=f"callback:{action.action_type}", result="denied", bot_user_id=context.bot_user_id, project_id=project.id, metadata_={"reason": "permission"})
                    return "Kamu tidak berwenang menjalankan aksi ini."
                if runner_action:
                    if action.processing_at is not None and action.processing_at > now - timedelta(minutes=2):
                        return CallbackReply(text=None, send_message=False, callback_text="⏳ Workflow masih diproses. Tunggu sampai selesai.")
                    action.processing_at = now
                    original_markup = action.target.get("reply_markup") if isinstance(action.target.get("reply_markup"), dict) else None
                    if original_markup is None and edit_message_id is not None:
                        notification = await self.repository.notification_by_message(session, project_id=project.id, chat_id=chat.id, message_id=edit_message_id)
                        original_markup = notification.reply_markup if notification is not None else None
                    claim = CallbackClaim(action=action, project=project, instance=instance, identity=identity, edit_message_id=edit_message_id, original_reply_markup=original_markup)
                else:
                    action.consumed_at = now
        if selector_target is not None:
            return await self._handle_selector(context, selector_target, edit_message_id)
        if claim is not None:
            return claim
        try:
            result = await self._execute_callback(context, action, project, instance, identity)
            await self._audit(context, project.id, f"callback:{action.action_type}", "success", identity_id=identity.id, merge_request_iid=int(action.target.get("iid")) if action.target.get("iid") else None, merge_request_sha=action.expected_sha)
            return result
        except GitlabApiError as error:
            await self._audit(context, project.id, f"callback:{action.action_type}", f"gitlab_{error.status_code}", identity_id=identity.id, merge_request_iid=int(action.target.get("iid")) if action.target.get("iid") else None, merge_request_sha=action.expected_sha, metadata={"status_code": error.status_code})
            if error.status_code == 401:
                await self._disable_identity(identity.id)
                return "Token GitLab ditolak (401). Identity ditandai disconnected; reconnect dengan /gitlab."
            if error.status_code == 409:
                return "GitLab menolak karena state/HEAD SHA berubah. Muat ulang MR dari /mr sebelum mencoba lagi."
            return f"GitLab menolak aksi ini (HTTP {error.status_code})."

    async def execute_claimed_callback(self, context: UserContext, claim: CallbackClaim) -> str | CallbackReply:
        action = claim.action
        try:
            result = await self._execute_callback(context, action, claim.project, claim.instance, claim.identity)
            if isinstance(result, str):
                await self._release_callback(action.id)
                await self._audit(context, claim.project.id, f"callback:{action.action_type}", "failed", identity_id=claim.identity.id, metadata={"reason": result[:300]})
                return _manual_failure_reply(claim, result)
            await self._finalize_callback(action.id)
            await self._audit(context, claim.project.id, f"callback:{action.action_type}", "success", identity_id=claim.identity.id, merge_request_iid=int(action.target.get("iid")) if action.target.get("iid") else None, merge_request_sha=action.expected_sha)
            if result.edit_message_id is None and claim.edit_message_id is not None:
                return _with_edit_message(result, claim.edit_message_id)
            return result
        except GitlabApiError as error:
            await self._release_callback(action.id)
            await self._audit(context, claim.project.id, f"callback:{action.action_type}", f"gitlab_{error.status_code}", identity_id=claim.identity.id, merge_request_iid=int(action.target.get("iid")) if action.target.get("iid") else None, merge_request_sha=action.expected_sha, metadata={"status_code": error.status_code})
            if error.status_code == 401:
                await self._disable_identity(claim.identity.id)
            return _manual_failure_reply(claim, _gitlab_error_text(error))
        except Exception as error:
            await self._release_callback(action.id)
            await self._audit(context, claim.project.id, f"callback:{action.action_type}", "failed", identity_id=claim.identity.id, metadata={"error_type": type(error).__name__})
            return _manual_failure_reply(claim, f"Manual run gagal: {_escape(str(error)[:400])}")

    async def handle_callback(self, context: UserContext, callback_data: str, *, edit_message_id: int | None = None) -> str | CallbackReply:
        prepared = await self.claim_callback(context, callback_data, edit_message_id=edit_message_id)
        if isinstance(prepared, CallbackClaim):
            return await self.execute_claimed_callback(context, prepared)
        return prepared

    async def loading_reply(self, claim: CallbackClaim, callback_data: str) -> CallbackReply:
        return CallbackReply(
            text=None,
            reply_markup=_loading_markup(claim.original_reply_markup, callback_data),
            edit_message_id=claim.edit_message_id,
            edit_markup_only=True,
            send_message=False,
        )

    async def _finalize_callback(self, action_id: int) -> None:
        async with self.database.transaction() as session:
            action = await session.get(GitlabCallbackActionModel, action_id, with_for_update=True)
            if action is not None:
                action.processing_at = None
                action.consumed_at = utc_now()

    async def _release_callback(self, action_id: int) -> None:
        async with self.database.transaction() as session:
            action = await session.get(GitlabCallbackActionModel, action_id, with_for_update=True)
            if action is not None and action.consumed_at is None:
                action.processing_at = None

    async def _execute_callback(self, context: UserContext, action: GitlabCallbackActionModel, project: GitlabProjectModel, instance: GitlabInstanceModel, identity: GitlabUserIdentityModel) -> str | CallbackReply:
        client = self._client(instance, identity)
        if action.action_type in (ACTION_RUN_MANUAL_SCRIPT, ACTION_CONFIRM_MANUAL_SCRIPT, ACTION_APPROVE_AND_RUN, ACTION_CONFIRM_APPROVE_AND_RUN):
            return await self._execute_manual_script_action(context, action, project, client)
        if action.action_type in (ACTION_INVOKE_PROMOTION, ACTION_INVOKE_PRODUCTION):
            async with self.database.session() as session:
                rule = await session.get(GitlabPromotionRuleModel, int(action.target["rule_id"]))
            if rule is None or not rule.enabled:
                return "Promotion rule sudah tidak aktif."
            open_mrs = await client.merge_requests(project.external_project_id, source_branch=rule.source_branch, target_branch=rule.target_branch)
            if open_mrs:
                return f"MR yang sama sudah terbuka: !{open_mrs[0].iid}. Bot tidak membuat duplikat."
            if not rule.mr_required:
                return "Promotion tanpa MR belum diaktifkan di MVP."
            mr = await client.create_merge_request(project.external_project_id, source_branch=rule.source_branch, target_branch=rule.target_branch, title=f"Promote {rule.source_branch} to {rule.target_branch}")
            return f"MR !{mr.iid} dibuat untuk <code>{_escape(rule.source_branch)} → {_escape(rule.target_branch)}</code>."
        iid = int(action.target["iid"])
        mr = await client.merge_request(project.external_project_id, iid)
        if mr.state != "opened" or not mr.sha or mr.sha != action.expected_sha:
            return "Aksi stale: HEAD MR sudah berubah atau MR tidak lagi terbuka."
        if action.action_type == ACTION_APPROVE_MR:
            await client.approve(project.external_project_id, iid, sha=action.expected_sha)
            return f"MR !{iid} di-approve dengan SHA yang sudah diverifikasi."
        if action.action_type == ACTION_MERGE_MR:
            approvals = await client.approvals(project.external_project_id, iid)
            if approvals.get("approvals_left", 0) > 0:
                return "Merge ditahan: approval GitLab yang diwajibkan belum lengkap."
            if mr.detailed_merge_status not in ("mergeable", "ci_must_pass"):
                return f"Merge ditahan oleh GitLab: detailed_merge_status={mr.detailed_merge_status}."
            async with self.database.session() as session:
                rules = await self.repository.rules(session, project_id=project.id)
            for rule in rules:
                if rule.target_branch != mr.target_branch:
                    continue
                if rule.successful_pipeline_required:
                    pipelines = await client.pipelines(project.external_project_id, ref=mr.source_branch)
                    if not pipelines or pipelines[0].status != "success":
                        return "Merge ditahan: pipeline yang diwajibkan promotion rule belum sukses."
                break
            await client.merge(project.external_project_id, iid, sha=action.expected_sha)
            return f"MR !{iid} dikirim ke endpoint merge GitLab dengan SHA yang diverifikasi."
        return "Tipe aksi belum didukung."

    async def _execute_manual_script_action(self, context: UserContext, action: GitlabCallbackActionModel, project: GitlabProjectModel, client: GitlabApiClient) -> str | CallbackReply:
        mapping_id = int(action.target["mapping_id"])
        async with self.database.session() as session:
            mapping = await self.repository.manual_mapping(session, mapping_id)
        if mapping is None or not mapping.active or mapping.project_id != project.id:
            return "Manual script mapping sudah tidak aktif."
        branch = await client.branch(project.external_project_id, mapping.target_branch)
        current_sha = str(branch.commit.get("id") or "")
        if action.action_type in (ACTION_RUN_MANUAL_SCRIPT, ACTION_CONFIRM_MANUAL_SCRIPT) and (not current_sha or current_sha != action.expected_sha):
            return "Aksi stale: branch sudah menerima push baru. Gunakan tombol dari notifikasi terbaru."
        if action.action_type in (ACTION_RUN_MANUAL_SCRIPT, ACTION_APPROVE_AND_RUN) and branch.protected:
            confirmation_type = ACTION_CONFIRM_MANUAL_SCRIPT if action.action_type == ACTION_RUN_MANUAL_SCRIPT else ACTION_CONFIRM_APPROVE_AND_RUN
            key = f"glo:v1:{secrets.token_urlsafe(12)}"
            confirmation_markup = action_markup([(f"⚠️ Confirm run {mapping.telegram_label}", key)]) or {"inline_keyboard": []}
            confirmation_target = dict(action.target)
            confirmation_target["reply_markup"] = confirmation_markup
            async with self.database.transaction() as session:
                session.add(GitlabCallbackActionModel(action_key=key.removeprefix("glo:v1:"), action_type=confirmation_type, project_id=project.id, target=confirmation_target, expected_sha=action.expected_sha, requester_bot_user_id=context.bot_user_id, chat_id=action.chat_id, expires_at=utc_now() + timedelta(minutes=15)))
            return CallbackReply(
                text=f"Branch <code>{_escape(mapping.target_branch)}</code> protected. Konfirmasi kedua diperlukan untuk menjalankan <b>{_escape(mapping.telegram_label)}</b>.",
                reply_markup=confirmation_markup,
            )
        if action.action_type in (ACTION_APPROVE_AND_RUN, ACTION_CONFIRM_APPROVE_AND_RUN):
            iid = int(action.target["iid"])
            mr = await client.merge_request(project.external_project_id, iid)
            if mr.state != "opened" or not mr.sha or mr.sha != action.expected_sha:
                return "Aksi stale: HEAD MR sudah berubah atau MR tidak lagi terbuka."
            await client.approve(project.external_project_id, iid, sha=action.expected_sha)
            branch = await client.branch(project.external_project_id, mapping.target_branch)
        current_sha = str(branch.commit.get("id") or "")
        if not current_sha:
            return "GitLab tidak mengembalikan SHA branch terbaru. Run dibatalkan."
        if action.action_type in (ACTION_RUN_MANUAL_SCRIPT, ACTION_CONFIRM_MANUAL_SCRIPT) and current_sha != action.expected_sha:
            return "Aksi stale: branch sudah menerima push baru. Gunakan tombol dari notifikasi terbaru."
        origin_message_id = await self._origin_message_id(project.id, action.chat_id, action.target.get("origin_resource_id"), action.target.get("origin_resource_type", "push"))
        async with self.database.transaction() as session:
            run = await self.repository.add_manual_run(session, mapping_id=mapping.id, project_id=project.id, telegram_chat_id=action.chat_id, origin_message_id=origin_message_id, ref=mapping.target_branch, commit_sha=current_sha, actor_bot_user_id=context.bot_user_id)
        try:
            pipeline = await client.create_pipeline(project.external_project_id, ref=mapping.target_branch)
            await self._finish_manual_run(run.id, status="requested", pipeline_id=pipeline.id)
            jobs: list[dict] = []
            for _ in range(3):
                jobs = await client.pipeline_jobs(project.external_project_id, pipeline.id)
                if jobs:
                    break
                await asyncio.sleep(1)
            job = next((item for item in jobs if str(item.get("name")) == mapping.job_name), None)
            if job is None:
                await self._finish_manual_run(run.id, status="failed", failure_reason=f"Job {mapping.job_name} tidak ditemukan pada pipeline API.", pipeline_id=pipeline.id)
                return f"Pipeline #{pipeline.id} dibuat, tetapi job <code>{_escape(mapping.job_name)}</code> tidak ditemukan."
            if str(job.get("when") or "") != "manual" and str(job.get("status") or "") != "manual":
                await self._finish_manual_run(run.id, status="failed", failure_reason="Job yang dipetakan bukan manual pada pipeline efektif.", pipeline_id=pipeline.id, job_id=int(job["id"]))
                return "Job ditemukan, tetapi GitLab tidak menandainya sebagai manual. Run dibatalkan."
            played = await client.play_job(project.external_project_id, int(job["id"]))
            await self._finish_manual_run(run.id, status="running", pipeline_id=pipeline.id, job_id=int(job["id"]), job_url=played.get("web_url") or job.get("web_url"))
            run.status = "running"
            run.pipeline_id = pipeline.id
            run.job_id = int(job["id"])
            run.job_url = played.get("web_url") or job.get("web_url")
            return CallbackReply(text=_manual_run_text(project, mapping, run), reply_markup={"inline_keyboard": []}, edit_message_id=origin_message_id)
        except GitlabApiError as error:
            await self._finish_manual_run(run.id, status="failed", failure_reason=f"GitLab HTTP {error.status_code}: {str(error)[:300]}")
            raise

    async def _origin_message_id(self, project_id: int, chat_id: int, resource_id: str | None, resource_type: str) -> int | None:
        if not resource_id:
            return None
        async with self.database.session() as session:
            message = await self.repository.notification(session, project_id=project_id, chat_id=chat_id, resource_type=resource_type, external_resource_id=resource_id)
            return message.telegram_message_id if message else None

    async def _finish_manual_run(self, run_id: int, *, status: str, failure_reason: str | None = None, pipeline_id: int | None = None, job_id: int | None = None, job_url: str | None = None) -> None:
        async with self.database.transaction() as session:
            run = await self.repository.manual_run(session, run_id)
            if run is None:
                return
            terminal_status = run.status in {"success", "failed", "canceled", "skipped"}
            if not (status == "running" and terminal_status):
                run.status = status
                run.failure_reason = failure_reason
            if pipeline_id is not None:
                run.pipeline_id = pipeline_id
            if job_id is not None:
                run.job_id = job_id
            if job_url is not None:
                run.job_url = job_url

    async def _process_event(self, telegram: TelegramBotClient, row: GitlabWebhookInboxModel) -> None:
        async with self.database.session() as session:
            webhook = await session.get(GitlabProjectWebhookModel, row.webhook_id)
            project = await session.get(GitlabProjectModel, webhook.project_id) if webhook else None
            if project is None:
                return
            payload = row.normalized_payload
            category, branch = _event_category(row.event_type, payload)
            if category is None:
                return
            if category == "job":
                await self._process_job_event(telegram, project, payload)
                return
            subscriptions = await self.repository.subscriptions(session, project_id=project.id, category=category)
            chats = {subscription.telegram_chat_id: await session.get(TelegramChatModel, subscription.telegram_chat_id) for subscription in subscriptions}
        if not subscriptions:
            return
        fingerprint = _fingerprint(json.dumps(payload, sort_keys=True, default=str))
        for subscription in subscriptions:
            chat = chats[subscription.telegram_chat_id]
            status = str((payload.get("object_attributes") or payload).get("status") or payload.get("status") or "").lower()
            if chat is None or not branch_matches(branch, list(subscription.branch_patterns)) or (category == "pipeline" and subscription.pipeline_mode == "failures" and status in {"success", "skipped", "manual"}):
                continue
            text, resource_type, resource_id = self._event_text(project, category, payload, row.event_type)
            async with self.database.transaction() as session:
                message = await self.repository.notification(session, project_id=project.id, chat_id=chat.id, resource_type=resource_type, external_resource_id=resource_id)
                if message and message.last_event_fingerprint == fingerprint:
                    continue
                was_running = category == "pipeline" and message is not None and message.last_status == "running"
                actions: list[tuple[str, str]] = []
                if category == "merge_request":
                    authorized = await session.scalar(select(GitlabProjectPermissionModel).where(GitlabProjectPermissionModel.project_id == project.id, GitlabProjectPermissionModel.allowed_chat_id.is_(None) | (GitlabProjectPermissionModel.allowed_chat_id == chat.id), GitlabProjectPermissionModel.active.is_(True)).order_by(GitlabProjectPermissionModel.bot_user_id))
                    if authorized and ACTION_APPROVE_MR in authorized.action_set:
                        approve_key = await self._create_callback_in_session(session, action_type=ACTION_APPROVE_MR, project_id=project.id, target={"iid": payload.get("object_attributes", {}).get("iid")}, expected_sha=payload.get("object_attributes", {}).get("last_commit", {}).get("id"), bot_user_id=authorized.bot_user_id, chat_row_id=chat.id)
                        actions.append(("Approve", approve_key))
                    if authorized and ACTION_MERGE_MR in authorized.action_set:
                        merge_key = await self._create_callback_in_session(session, action_type=ACTION_MERGE_MR, project_id=project.id, target={"iid": payload.get("object_attributes", {}).get("iid")}, expected_sha=payload.get("object_attributes", {}).get("last_commit", {}).get("id"), bot_user_id=authorized.bot_user_id, chat_row_id=chat.id)
                        actions.append(("Merge", merge_key))
                    attrs = payload.get("object_attributes") or payload
                    target_branch = attrs.get("target_branch")
                    mr_sha = (attrs.get("last_commit") or {}).get("id")
                    for mapping in await self.repository.manual_mappings(session, project_id=project.id, target_branch=target_branch):
                        script_permission = await session.scalar(select(GitlabManualScriptPermissionModel).where(GitlabManualScriptPermissionModel.mapping_id == mapping.id, GitlabManualScriptPermissionModel.active.is_(True)).order_by(GitlabManualScriptPermissionModel.bot_user_id))
                        if authorized and script_permission and ACTION_APPROVE_MR in authorized.action_set:
                            action_key = await self._create_callback_in_session(session, action_type=ACTION_APPROVE_AND_RUN, project_id=project.id, target={"iid": attrs.get("iid"), "mapping_id": mapping.id, "origin_resource_id": str(attrs.get("iid") or ""), "origin_resource_type": "merge_request"}, expected_sha=mr_sha, bot_user_id=script_permission.bot_user_id, chat_row_id=chat.id)
                            label = f"Approve & Run {mapping.telegram_label}"
                            if attrs.get("target_branch") in {"main", "master", "production"}:
                                label = f"⚠️ Approve & Run {mapping.telegram_label}"
                            actions.append((label, action_key))
                if category == "push":
                    push_sha = str(payload.get("after") or payload.get("checkout_sha") or "")
                    for mapping in await self.repository.manual_mappings(session, project_id=project.id, target_branch=branch):
                        script_permission = await session.scalar(select(GitlabManualScriptPermissionModel).where(GitlabManualScriptPermissionModel.mapping_id == mapping.id, GitlabManualScriptPermissionModel.active.is_(True)).order_by(GitlabManualScriptPermissionModel.bot_user_id))
                        if script_permission and push_sha:
                            action_key = await self._create_callback_in_session(session, action_type=ACTION_RUN_MANUAL_SCRIPT, project_id=project.id, target={"mapping_id": mapping.id, "origin_resource_id": str(payload.get("after") or payload.get("checkout_sha") or "")}, expected_sha=push_sha, bot_user_id=script_permission.bot_user_id, chat_row_id=chat.id)
                            actions.append((f"Run {mapping.telegram_label}", action_key))
                markup = action_markup(actions)
            sent: SentMessage
            if was_running and message is not None:
                sent = await telegram.send_message(chat_id=chat.telegram_chat_id, text=text, parse_mode="HTML", reply_markup=markup)
                try:
                    await telegram.delete_message(chat_id=chat.telegram_chat_id, message_id=message.telegram_message_id)
                except Exception:
                    await logger.aexception("gitlab_notification_delete_failed", project_id=project.id, chat_id=chat.telegram_chat_id, message_id=message.telegram_message_id)
            elif message:
                try:
                    sent = await telegram.edit_message(chat_id=chat.telegram_chat_id, message_id=message.telegram_message_id, text=text, parse_mode="HTML", reply_markup=markup)
                except Exception:
                    sent = await telegram.send_message(chat_id=chat.telegram_chat_id, text=text, parse_mode="HTML", reply_markup=markup)
            else:
                sent = await telegram.send_message(chat_id=chat.telegram_chat_id, text=text, parse_mode="HTML", reply_markup=markup)
            async with self.database.transaction() as session:
                await self.repository.save_notification(session, project_id=project.id, chat_id=chat.id, resource_type=resource_type, external_resource_id=resource_id, message_id=sent.message_id, fingerprint=fingerprint, status=status or None, reply_markup=markup)

    async def _process_job_event(self, telegram: TelegramBotClient, project: GitlabProjectModel, payload: dict[str, Any]) -> None:
        attrs = payload.get("object_attributes") or payload
        job_id = _int_value(attrs.get("id") or attrs.get("build_id") or payload.get("build_id"))
        pipeline = attrs.get("pipeline") or payload.get("pipeline") or {}
        pipeline_id = _int_value(pipeline.get("id") if isinstance(pipeline, dict) else pipeline) or _int_value(attrs.get("pipeline_id") or payload.get("pipeline_id"))
        job_name = attrs.get("name") or attrs.get("build_name") or payload.get("build_name")
        status = str(attrs.get("status") or attrs.get("build_status") or payload.get("build_status") or "unknown").lower()
        if job_id is None and pipeline_id is None:
            return
        async with self.database.transaction() as session:
            run = await self.repository.manual_run_by_external(session, project_id=project.id, job_id=job_id, pipeline_id=pipeline_id)
            if run is None:
                return
            mapping = await self.repository.manual_mapping(session, run.mapping_id)
            chat = await session.get(TelegramChatModel, run.telegram_chat_id)
            if mapping is None or chat is None:
                return
            if job_name is not None and str(job_name) != mapping.job_name:
                return
            was_terminal = run.status in {"success", "failed", "canceled", "skipped"}
            run.status = status
            run.job_id = job_id or run.job_id
            run.pipeline_id = pipeline_id or run.pipeline_id
            run.job_url = attrs.get("web_url") or attrs.get("build_url") or payload.get("build_url") or run.job_url
            run.failure_reason = _job_failure_reason(attrs) if status in {"failed", "canceled"} else None
            message_id = run.origin_message_id
            text = _manual_run_text(project, mapping, run)
            if was_terminal:
                return
            if status in {"success", "failed", "canceled", "skipped"}:
                sent = await telegram.send_message(chat_id=chat.telegram_chat_id, text=text, parse_mode="HTML", reply_markup={"inline_keyboard": []})
                if message_id is not None:
                    try:
                        await telegram.delete_message(chat_id=chat.telegram_chat_id, message_id=message_id)
                    except Exception:
                        await logger.aexception("gitlab_manual_run_origin_delete_failed", project_id=project.id, chat_id=chat.telegram_chat_id, message_id=message_id, result_message_id=sent.message_id)
            elif message_id is not None:
                try:
                    await telegram.edit_message(chat_id=chat.telegram_chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup={"inline_keyboard": []})
                except Exception:
                    pass

    async def _create_callback_in_session(self, session, *, action_type: str, project_id: int | None, target: dict[str, Any], expected_sha: str | None, bot_user_id: int, chat_row_id: int) -> str:
        key = secrets.token_urlsafe(12)
        session.add(GitlabCallbackActionModel(action_key=key, action_type=action_type, project_id=project_id, target=target, expected_sha=expected_sha, requester_bot_user_id=bot_user_id, chat_id=chat_row_id, expires_at=utc_now() + timedelta(minutes=15)))
        return f"glo:v1:{key}"

    async def _reconcile_hook(self, client: GitlabApiClient, external_project_id: int, webhook: GitlabProjectWebhookModel, url: str, secret: str, trigger: dict[str, bool]) -> dict:
        if webhook.external_webhook_id is not None:
            return await client.update_hook(external_project_id, webhook.external_webhook_id, url=url, token=secret, trigger_config=trigger)
        return await client.create_hook(external_project_id, url=url, token=secret, trigger_config=trigger)

    async def _identity_for_user(self, session, telegram_user_id: int, *, for_update: bool = False, instance_id: int | None = None) -> GitlabUserIdentityModel | None:
        if instance_id is not None:
            return await self.repository.identity_for_instance(session, telegram_user_id=telegram_user_id, instance_id=instance_id, for_update=for_update)
        statement = select(GitlabUserIdentityModel).where(GitlabUserIdentityModel.telegram_user_id == telegram_user_id, GitlabUserIdentityModel.status == "active").order_by(GitlabUserIdentityModel.id)
        if for_update:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    def _client(self, instance: GitlabInstanceModel, identity: GitlabUserIdentityModel) -> GitlabApiClient:
        return GitlabApiClient(self.http, instance.base_url, self.cipher.decrypt(identity.token_ciphertext).get_secret_value())

    def _verify_webhook(self, webhook: GitlabProjectWebhookModel, headers: dict[str, str], raw_body: bytes) -> bool:
        provided = headers.get("x-gitlab-token") or headers.get("x-gitlab-webhook-token")
        if not provided:
            return False
        expected = self.cipher.decrypt(webhook.secret_ciphertext).get_secret_value().encode()
        return hmac.compare_digest(provided.encode(), expected)

    async def _disable_identity(self, identity_id: int) -> None:
        async with self.database.transaction() as session:
            identity = await session.get(GitlabUserIdentityModel, identity_id, with_for_update=True)
            if identity:
                identity.status = "disconnected"

    async def _audit(self, context: UserContext, project_id: int | None, action: str, result: str, **values: Any) -> None:
        metadata = values.pop("metadata", None)
        if metadata is not None:
            values["metadata_"] = metadata
        async with self.database.transaction() as session:
            await self.repository.audit(session, action=action, result=result, telegram_user_id=context.internal_user_id, bot_user_id=context.bot_user_id, project_id=project_id, **values)

    @staticmethod
    def _event_text(project: GitlabProjectModel, category: str, payload: dict[str, Any], event_type: str) -> tuple[str, str, str]:
        if category == "merge_request":
            attrs = payload.get("object_attributes") or payload
            return mr_text(project, attrs, event=event_type), "merge_request", str(attrs.get("iid") or attrs.get("id") or "unknown")
        if category == "pipeline":
            attrs = payload.get("object_attributes") or payload
            return pipeline_text(project, attrs), "pipeline", str(attrs.get("id") or "unknown")
        if category == "deployment":
            attrs = payload.get("deployment") or payload
            return deployment_text(project, attrs), "deployment", str(attrs.get("id") or "unknown")
        return push_text(project, payload), "push", str(payload.get("after") or payload.get("checkout_sha") or _fingerprint(json.dumps(payload, sort_keys=True)))


class GitlabEventExecutor:
    def __init__(self, service: GitlabOpsService, telegram: TelegramBotClient, *, enabled: bool, interval_seconds: int, batch_size: int) -> None:
        self._service = service
        self._telegram = telegram
        self._enabled = enabled
        self._interval = interval_seconds
        self._batch_size = batch_size
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._enabled:
            self._task = asyncio.create_task(self._run(), name="gitlab-ops-event-executor")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _run(self) -> None:
        while True:
            await self._service.process_pending(self._telegram, batch_size=self._batch_size)
            await asyncio.sleep(self._interval)


def _event_category(event_type: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    value = event_type.lower()
    if "job" in value:
        attrs = payload.get("object_attributes") or payload
        return "job", attrs.get("ref")
    if "merge_request" in value:
        attrs = payload.get("object_attributes") or payload
        return "merge_request", attrs.get("target_branch") or attrs.get("source_branch")
    if "pipeline" in value:
        attrs = payload.get("object_attributes") or payload
        return "pipeline", attrs.get("ref")
    if "deployment" in value:
        attrs = payload.get("deployment") or payload
        return "deployment", attrs.get("ref") or attrs.get("environment")
    if "push" in value:
        return "push", str(payload.get("ref") or "").removeprefix("refs/heads/")
    return None, None


def _page_bounds(total_items: int, page: int) -> tuple[int, int]:
    total_pages = max(1, (total_items + SELECTOR_PAGE_SIZE - 1) // SELECTOR_PAGE_SIZE)
    return min(max(page, 0), total_pages - 1), total_pages


def selector_label(flow: str) -> str:
    return {
        SELECTOR_DEPLOY: "promotion",
        SELECTOR_BRANCHES: "branches",
        SELECTOR_SCRIPTS: "manual scripts",
        SELECTOR_RULE: "promotion rule",
        SELECTOR_SUBSCRIBE: "subscription",
        SELECTOR_SCRIPT_GRANT: "grant manual script",
    }.get(flow, "operasi GitLab")


def _with_edit_message(reply: CallbackReply | str, message_id: int | None) -> CallbackReply | str:
    if isinstance(reply, CallbackReply):
        return CallbackReply(text=reply.text, reply_markup=reply.reply_markup, edit_message_id=message_id, next_state=reply.next_state, next_state_data=reply.next_state_data, edit_markup_only=reply.edit_markup_only, send_message=reply.send_message, callback_text=reply.callback_text)
    return reply


def _loading_markup(reply_markup: dict[str, Any] | None, callback_data: str) -> dict[str, Any] | None:
    if reply_markup is None:
        return None
    markup = json.loads(json.dumps(reply_markup))
    for row in markup.get("inline_keyboard", []):
        for button in row:
            if button.get("callback_data") == callback_data:
                label = str(button.get("text") or "aksi")
                button["text"] = f"⏳ Menjalankan {label}"
    return markup


def _manual_failure_reply(claim: CallbackClaim, text: str) -> CallbackReply:
    return CallbackReply(
        text=text,
        reply_markup=claim.original_reply_markup,
        edit_message_id=claim.edit_message_id,
        edit_markup_only=claim.edit_message_id is not None,
    )


def _gitlab_error_text(error: GitlabApiError) -> str:
    if error.status_code == 401:
        return "Token GitLab ditolak (401). Identity ditandai disconnected; reconnect dengan /gitlab."
    if error.status_code == 409:
        return "GitLab menolak karena state/HEAD SHA berubah. Muat ulang notifikasi sebelum mencoba lagi."
    return f"GitLab menolak manual run ini (HTTP {error.status_code}): {_escape(str(error)[:300])}"


def _sanitize_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if isinstance(value, dict):
        return {str(key): _sanitize_payload(item, depth=depth + 1) for key, item in value.items() if str(key).lower() not in {"token", "secret", "private_token", "authorization", "password"}}
    if isinstance(value, list):
        return [_sanitize_payload(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return value[:10_000]
    return value


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _escape(value: str, *, quote: bool = False) -> str:
    from html import escape
    return escape(value, quote=quote)


def _job_failure_reason(payload: dict[str, Any]) -> str:
    reason = payload.get("failure_reason") or payload.get("failure_reason_description") or payload.get("status") or "job gagal"
    return str(reason)[:300]


def _int_value(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _manual_run_text(project: GitlabProjectModel, mapping: GitlabManualScriptMappingModel, run: GitlabManualScriptRunModel) -> str:
    status = run.status.capitalize()
    link = f' · <a href="{_escape(run.job_url, quote=True)}">Lihat log di GitLab</a>' if run.job_url else ""
    failure = f"\nReason: <code>{_escape(run.failure_reason)}</code>" if run.failure_reason else ""
    return f"<b>{status} {_escape(mapping.telegram_label)}</b>\n{_escape(project.namespace_path)} · <code>{_escape(run.ref)}</code>\nSHA: <code>{_escape(run.commit_sha[:12])}</code>{link}{failure}"
