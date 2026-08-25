from __future__ import annotations

from html import escape
from typing import Any

from app.core.logging import get_logger
from app.core.telegram_client import TelegramBotClient
from app.modules.gitlab_ops.gitlab_client import normalize_gitlab_url
from app.modules.gitlab_ops.schemas import ManualScriptMappingInput, PromotionRuleInput, SubscriptionInput
from app.modules.gitlab_ops.services import (
    CallbackClaim,
    CallbackReply,
    GitlabOpsService,
    SELECTOR_BRANCHES,
    SELECTOR_DEPLOY,
    SELECTOR_RULE,
    SELECTOR_SCRIPT_GRANT,
    SELECTOR_SCRIPTS,
    SELECTOR_SUBSCRIBE,
    SELECTOR_AUTOMATION,
)
from app.platform.users.services import UserStateService
from app.shared.types import TelegramUpdate, UserContext

logger = get_logger(__name__)


class GitlabOpsRouter:
    def __init__(self, service: GitlabOpsService, state: UserStateService, telegram: TelegramBotClient) -> None:
        self._service = service
        self._state = state
        self._telegram = telegram

    async def dispatch(self, update: TelegramUpdate, context: UserContext) -> None:
        if update.callback_query is not None:
            await self._handle_callback(update.callback_query.id, update.callback_query.data, context, update.callback_query.message.message_id if update.callback_query.message else None)
            return
        message = update.message
        if message is None or message.text is None:
            return
        if message.chat.type == "private":
            await self._handle_private(message.text.strip(), context)
            return
        await self._handle_group(message.text.strip(), context)

    async def _handle_private(self, text: str, context: UserContext) -> None:
        command, args = _command(text)
        if command == "/gitlab":
            if args.lower() in ("", "connect", "status"):
                if args.lower() == "status":
                    await self._send(context.chat_id, await self._status(context))
                    return
                await self._state.set_state(context.bot_user_id, state="gitlab_await_url", data={}, expected_version=(await self._state.get_state(context.bot_user_id)).version)
                await self._send(context.chat_id, "Kirim HTTPS GitLab base URL (contoh: https://gitlab.com). Token hanya boleh dikirim di private chat ini.")
                return
            if args.lower() == "projects":
                await self._show_project_picker(context)
                return
            if args.lower() == "branches":
                await self._show_selector(context, SELECTOR_BRANCHES)
                return
            if args.lower().startswith("branches "):
                try:
                    await self._send(context.chat_id, await self._service.show_branches(context, int(args[9:].strip())))
                except Exception as error:
                    await self._send(context.chat_id, f"Gagal mengambil branches: {escape(str(error))[:400]}")
                return
            if args.lower() == "scripts":
                await self._show_selector(context, SELECTOR_SCRIPTS)
                return
            if args.lower().startswith("scripts "):
                await self._start_script_wizard(context, args[8:].strip())
                return
            if args.lower() == "script grant":
                await self._show_selector(context, SELECTOR_SCRIPT_GRANT)
                return
            if args.lower().startswith("script grant "):
                await self._grant_script(context, args[13:].strip())
                return
            if args.lower().startswith("automation"):
                await self._automation(context, args[10:].strip())
                return
            if args.lower().startswith("project "):
                await self._select_project(context, args[8:].strip())
                return
            if args.lower() == "rule":
                await self._show_selector(context, SELECTOR_RULE)
                return
            if args.lower().startswith("rule "):
                await self._save_rule(context, args[5:])
                return
            if args.lower() == "subscribe":
                await self._show_selector(context, SELECTOR_SUBSCRIBE)
                return
            if args.lower().startswith("subscribe "):
                await self._save_subscription(context, args[10:])
                return
            await self._send(context.chat_id, "Gunakan /gitlab projects, /gitlab branches, /gitlab scripts, /gitlab automation, /gitlab rule, /gitlab subscribe, /gitlab script grant, atau /gitlab status.")
            return
        if command == "/projects":
            await self._send(context.chat_id, await self._service.list_projects_text(context))
            return
        if command == "/deploy":
            if not args:
                await self._show_selector(context, SELECTOR_DEPLOY)
                return
            await self._deploy(args, context)
            return
        if command == "/mr":
            await self._send(context.chat_id, await self._service.show_mrs(context))
            return
        if command == "/pipeline":
            await self._send(context.chat_id, await self._service.show_pipelines(context))
            return
        state = await self._state.get_state(context.bot_user_id)
        if state.state is not None:
            await self._handle_state(text, context, state.state, dict(state.data), state.version)

    async def _handle_group(self, text: str, context: UserContext) -> None:
        command, args = _command(text)
        if command == "/projects":
            await self._send(context.chat_id, await self._service.list_projects_text(context))
        elif command == "/mr":
            await self._send(context.chat_id, await self._service.show_mrs(context))
        elif command == "/pipeline":
            await self._send(context.chat_id, await self._service.show_pipelines(context))
        elif command == "/deploy":
            await self._deploy(args, context)
        elif command == "/gitlab" and args.lower() == "subscribe":
            await self._show_selector(context, SELECTOR_SUBSCRIBE)
        elif command == "/gitlab":
            await self._send(context.chat_id, "Setup identity dan token GitLab hanya dilakukan di private chat. Di group, gunakan /gitlab subscribe untuk menerima notifikasi project ini.")
        else:
            state = await self._state.get_state(context.bot_user_id)
            if state.state == "gitlab_subscribe_input":
                await self._handle_state(text, context, state.state, dict(state.data), state.version)

    async def _handle_state(self, text: str, context: UserContext, state: str, data: dict[str, Any], version: int) -> None:
        if state in {"gitlab_rule_input", "gitlab_subscribe_input", "gitlab_grant_user", "gitlab_automation_pat", "gitlab_automation_author"} and data.get("chat_id") != context.chat_id:
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, "Sesi GitLab ini terikat ke chat lain. Mulai ulang command selector.")
            return
        if state == "gitlab_await_url":
            try:
                normalized = normalize_gitlab_url(text)
            except ValueError as error:
                await self._send(context.chat_id, escape(str(error)))
                return
            await self._state.set_state(context.bot_user_id, state="gitlab_await_pat", data={"base_url": normalized}, expected_version=version)
            await self._send(context.chat_id, "Sekarang kirim GitLab Personal Access Token. Token akan divalidasi lalu langsung disimpan terenkripsi; jangan kirim token di group.")
        elif state == "gitlab_await_pat":
            try:
                reply = await self._service.connect_identity(context, str(data["base_url"]), text)
            except Exception as error:
                await self._send(context.chat_id, f"Gagal menghubungkan GitLab: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, reply + "\nGunakan /gitlab projects untuk memilih project.")
        elif state == "gitlab_automation_pat":
            try:
                result = await self._service.configure_automation(context, int(data["project_id"]), text)
            except Exception as error:
                await self._send(context.chat_id, f"Setup automation gagal: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)
            menu = await self._service.automation_menu_reply(context, int(data["project_id"]))
            if isinstance(menu, CallbackReply):
                await self._send_reply(context.chat_id, menu)
        elif state == "gitlab_automation_author":
            try:
                result = await self._service.add_automation_author(context, int(data["project_id"]), text)
            except Exception as error:
                await self._send(context.chat_id, f"Tambah allowlist gagal: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)
            menu = await self._service.automation_menu_reply(context, int(data["project_id"]))
            if isinstance(menu, CallbackReply):
                await self._send_reply(context.chat_id, menu)
        elif state == "gitlab_select_project":
            try:
                index = int(text) - 1
                project = data["projects"][index]
            except (ValueError, KeyError, IndexError, TypeError):
                await self._send(context.chat_id, "Balas dengan nomor project dari daftar.")
                return
            await self._state.clear_state(context.bot_user_id)
            try:
                await self._send(context.chat_id, await self._service.setup_project(context, project))
            except Exception as error:
                await self._send(context.chat_id, f"Setup project gagal: {escape(str(error))[:400]}")
        elif state == "gitlab_script_branch":
            try:
                index = int(text) - 1
                branch = data["branches"][index]
                project_id = int(data["project_id"])
                jobs = await self._service.script_job_options(context, project_id, str(branch["name"]))
            except Exception as error:
                await self._send(context.chat_id, f"Branch tidak valid atau CI gagal dibaca: {escape(str(error))[:400]}")
                return
            if not jobs:
                await self._send(context.chat_id, "Tidak ada job `when: manual` pada effective CI branch tersebut.")
                return
            current = await self._state.get_state(context.bot_user_id)
            await self._state.set_state(context.bot_user_id, state="gitlab_script_job", data={"project_id": project_id, "target_branch": branch["name"], "jobs": jobs}, expected_version=current.version)
            lines = [f"<b>Pilih manual job untuk {escape(str(branch['name']))}:</b>"]
            lines.extend(f"{number}. <code>{escape(str(job.get('name')))}</code> · stage={escape(str(job.get('stage') or '-'))}" for number, job in enumerate(jobs, 1))
            await self._send(context.chat_id, "\n".join(lines))
        elif state in {"gitlab_script_job", "gitlab_script_job_name"}:
            try:
                if state == "gitlab_script_job":
                    index = int(text) - 1
                    job_name = str(data["jobs"][index]["name"])
                else:
                    job_name = text.strip()
                    if not job_name:
                        raise ValueError
            except (ValueError, KeyError, IndexError, TypeError):
                await self._send(context.chat_id, "Kirim nama job manual yang valid.")
                return
            current = await self._state.get_state(context.bot_user_id)
            await self._state.set_state(context.bot_user_id, state="gitlab_script_label", data={"project_id": data["project_id"], "target_branch": data["target_branch"], "job_name": job_name, "manual_job_validation": data.get("manual_job_validation")}, expected_version=current.version)
            await self._send(context.chat_id, "Kirim label Telegram untuk job ini, misalnya `Run Development`.")
        elif state == "gitlab_script_label":
            try:
                values = ManualScriptMappingInput(target_branch=str(data["target_branch"]), job_name=str(data["job_name"]), telegram_label=text[:128])
                result = await self._service.save_script_mapping(
                    context,
                    int(data["project_id"]),
                    values,
                    validate_job=data.get("manual_job_validation") != "deferred",
                )
            except Exception as error:
                await self._send(context.chat_id, f"Mapping script gagal: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)
        elif state == "gitlab_rule_input":
            parts = [part.strip() for part in text.split("|", 2)]
            if len(parts) != 3:
                await self._send(context.chat_id, "Format rule: `nama | source | target`.")
                return
            try:
                result = await self._service.save_rule(context, int(data["project_id"]), PromotionRuleInput(display_name=parts[0], source_branch=parts[1], target_branch=parts[2]))
            except Exception as error:
                await self._send(context.chat_id, f"Gagal menyimpan rule: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)
        elif state == "gitlab_subscribe_input":
            parts = [part.strip() for part in text.split("|", 2)]
            if len(parts) < 1 or (len(parts) > 1 and parts[0] not in ("failures", "all")):
                await self._send(context.chat_id, "Format subscription: `failures|all | branch1,release/*`.")
                return
            mode = parts[0] if parts[0] in ("failures", "all") else "failures"
            patterns = [item.strip() for item in parts[1].split(",") if item.strip()] if len(parts) > 1 else []
            try:
                result = await self._service.save_subscription(context, int(data["project_id"]), SubscriptionInput(pipeline_mode=mode, branch_patterns=patterns))
            except Exception as error:
                await self._send(context.chat_id, f"Gagal menyimpan subscription: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)
        elif state == "gitlab_grant_user":
            try:
                telegram_user_id = int(text)
                result = await self._service.grant_script_permission(context, int(data["mapping_id"]), telegram_user_id)
            except Exception as error:
                await self._send(context.chat_id, f"Grant script gagal: {escape(str(error))[:400]}")
                return
            await self._state.clear_state(context.bot_user_id)
            await self._send(context.chat_id, result)

    async def _show_project_picker(self, context: UserContext) -> None:
        try:
            projects = await self._service.discover_projects(context)
        except Exception as error:
            await self._send(context.chat_id, f"Gagal mengambil project dari GitLab: {escape(str(error))[:400]}")
            return
        if not projects:
            await self._send(context.chat_id, "Tidak ada project yang bisa diakses identity ini.")
            return
        projects = projects[:50]
        state = await self._state.get_state(context.bot_user_id)
        await self._state.set_state(context.bot_user_id, state="gitlab_select_project", data={"projects": projects}, expected_version=state.version)
        lines = ["<b>Pilih project dengan membalas nomornya:</b>"]
        lines.extend(f"{index}. <code>{escape(str(project['path_with_namespace']))}</code>" for index, project in enumerate(projects, 1))
        await self._send(context.chat_id, "\n".join(lines))

    async def _start_script_wizard(self, context: UserContext, value: str) -> None:
        try:
            project_id = int(value)
            branches = await self._service.script_branch_options(context, project_id)
        except Exception as error:
            await self._send(context.chat_id, f"Gagal membaca branch project: {escape(str(error))[:400]}")
            return
        if not branches:
            await self._send(context.chat_id, "Tidak ada branch yang tersedia.")
            return
        current = await self._state.get_state(context.bot_user_id)
        await self._state.set_state(context.bot_user_id, state="gitlab_script_branch", data={"project_id": project_id, "branches": branches[:100]}, expected_version=current.version)
        lines = ["<b>Pilih target branch untuk manual script:</b>"]
        lines.extend(f"{number}. <code>{escape(str(branch['name']))}</code>{' · protected' if branch.get('protected') else ''}" for number, branch in enumerate(branches[:100], 1))
        await self._send(context.chat_id, "\n".join(lines))

    async def _grant_script(self, context: UserContext, value: str) -> None:
        parts = [part.strip() for part in value.split("|", 1)]
        if len(parts) != 2:
            await self._send(context.chat_id, "Gunakan /gitlab script grant untuk memilih project dan manual script terlebih dahulu.")
            return
        try:
            result = await self._service.grant_script_permission(context, int(parts[0]), int(parts[1]))
        except Exception as error:
            result = f"Grant script gagal: {escape(str(error))[:400]}"
        await self._send(context.chat_id, result)

    async def _automation(self, context: UserContext, value: str) -> None:
        parts = value.split()
        if not parts:
            await self._show_selector(context, SELECTOR_AUTOMATION)
            return
        try:
            if parts[0].lower() == "status" and len(parts) == 2:
                await self._send(context.chat_id, await self._service.automation_status(context, int(parts[1])))
                return
            if parts[0].lower() == "allow" and len(parts) == 3:
                await self._send(context.chat_id, await self._service.add_automation_author(context, int(parts[1]), parts[2]))
                return
            if parts[0].lower() == "remove" and len(parts) == 3:
                await self._send(context.chat_id, await self._service.remove_automation_author(context, int(parts[1]), int(parts[2])))
                return
            if len(parts) == 1:
                project_id = int(parts[0])
                state = await self._state.get_state(context.bot_user_id)
                await self._state.set_state(context.bot_user_id, state="gitlab_automation_pat", data={"project_id": project_id, "chat_id": context.chat_id}, expected_version=state.version)
                await self._send(context.chat_id, "Kirim PAT service account GitLab sekarang. Token harus memiliki scope api dan akses project untuk membaca MR/branch, approve, membuat pipeline, serta play manual job.")
                return
        except Exception as error:
            await self._send(context.chat_id, f"Automation gagal: {escape(str(error))[:400]}")
            return
        await self._send(context.chat_id, "Format automation tidak valid.")

    async def _select_project(self, context: UserContext, value: str) -> None:
        state = await self._state.get_state(context.bot_user_id)
        if state.state != "gitlab_select_project":
            await self._send(context.chat_id, "Jalankan /gitlab projects terlebih dahulu.")
            return
        await self._handle_state(value, context, state.state, dict(state.data), state.version)

    async def _save_rule(self, context: UserContext, value: str) -> None:
        parts = [part.strip() for part in value.split("|", 3)]
        if len(parts) != 4:
            await self._send(context.chat_id, "Gunakan /gitlab rule untuk memilih project, lalu kirim `nama | source | target`.")
            return
        try:
            project_id = int(parts[0])
            result = await self._service.save_rule(context, project_id, PromotionRuleInput(display_name=parts[1], source_branch=parts[2], target_branch=parts[3]))
        except Exception as error:
            result = f"Gagal menyimpan rule: {escape(str(error))[:400]}"
        await self._send(context.chat_id, result)

    async def _save_subscription(self, context: UserContext, value: str) -> None:
        parts = [part.strip() for part in value.split("|", 2)]
        if not parts:
            await self._send(context.chat_id, "Gunakan /gitlab subscribe untuk memilih project, lalu kirim `failures|all | branch1,release/*`.")
            return
        try:
            project_id = int(parts[0])
            mode = parts[1] if len(parts) > 1 and parts[1] in ("failures", "all") else "failures"
            patterns = [item.strip() for item in parts[2].split(",") if item.strip()] if len(parts) > 2 else []
            result = await self._service.save_subscription(context, project_id, SubscriptionInput(pipeline_mode=mode, branch_patterns=patterns))
        except Exception as error:
            result = f"Gagal menyimpan subscription: {escape(str(error))[:400]}"
        await self._send(context.chat_id, result)

    async def _deploy(self, args: str, context: UserContext) -> None:
        parts = [part.strip() for part in args.split("|", 1)]
        if len(parts) != 2:
            await self._send(context.chat_id, "Gunakan /deploy untuk memilih project dan promotion rule berlabel bisnis.")
            return
        try:
            prompt = await self._service.promotion_prompt(context, int(parts[0]), parts[1])
            if prompt is not None:
                await self._telegram.send_message(chat_id=context.chat_id, text=prompt[0], parse_mode="HTML", reply_markup=prompt[1])
                return
            result = await self._service.deploy(context, int(parts[0]), parts[1])
        except Exception as error:
            result = f"Promotion gagal: {escape(str(error))[:400]}"
        await self._send(context.chat_id, result)

    async def _handle_callback(self, callback_id: str, data: str | None, context: UserContext, message_id: int | None = None) -> None:
        try:
            prepared = await self._service.claim_callback(context, data or "", edit_message_id=message_id)
            if isinstance(prepared, CallbackClaim):
                await self._telegram.answer_callback_query(callback_query_id=callback_id)
                await self._apply_callback_reply(await self._service.loading_reply(prepared, data or ""), context)
                reply = await self._service.execute_claimed_callback(context, prepared)
            else:
                await self._telegram.answer_callback_query(callback_query_id=callback_id, text=prepared.callback_text if isinstance(prepared, CallbackReply) else None)
                reply = prepared
            if isinstance(reply, CallbackReply):
                await self._apply_callback_reply(reply, context)
            else:
                await self._send(context.chat_id, reply)
        except Exception as error:
            await logger.aexception(
                "gitlab_callback_processing_failed",
                error_type=type(error).__name__,
            )
            await self._send(context.chat_id, "Aksi GitLab gagal diproses.")

    async def _apply_callback_reply(self, reply: CallbackReply, context: UserContext) -> None:
        if reply.next_state is not None:
            current = await self._state.get_state(context.bot_user_id)
            await self._state.set_state(context.bot_user_id, state=reply.next_state, data=reply.next_state_data or {}, expected_version=current.version)
        if reply.edit_message_id is not None and reply.edit_markup_only:
            try:
                await self._telegram.edit_message_reply_markup(chat_id=context.chat_id, message_id=reply.edit_message_id, reply_markup=reply.reply_markup)
            except Exception:
                await logger.aexception("gitlab_callback_markup_update_failed", message_id=reply.edit_message_id)
        elif reply.edit_message_id is not None and reply.text is not None:
            try:
                await self._telegram.edit_message(chat_id=context.chat_id, message_id=reply.edit_message_id, text=reply.text, parse_mode="HTML", reply_markup=reply.reply_markup)
            except Exception:
                if reply.send_message:
                    await self._telegram.send_message(chat_id=context.chat_id, text=reply.text, parse_mode="HTML", reply_markup=reply.reply_markup)
                return
        should_send = reply.send_message and (reply.edit_message_id is None or reply.edit_markup_only)
        if should_send and reply.text is not None:
            await self._telegram.send_message(chat_id=context.chat_id, text=reply.text, parse_mode="HTML", reply_markup=reply.reply_markup)

    async def _show_selector(self, context: UserContext, flow: str) -> None:
        try:
            current = await self._state.get_state(context.bot_user_id)
            if current.state is not None:
                await self._state.clear_state(context.bot_user_id)
            reply = await self._service.selector_reply(context, flow)
            if isinstance(reply, CallbackReply):
                await self._send_reply(context.chat_id, reply)
            else:
                await self._send(context.chat_id, reply)
        except Exception as error:
            await self._send(context.chat_id, f"Selector GitLab gagal dimuat: {escape(str(error))[:400]}")

    async def _status(self, context: UserContext) -> str:
        rows = await self._service.identity_summary(context)
        return "<b>GitLab identities</b>\n" + "\n".join(escape(row) for row in rows) if rows else "Belum ada identity. Gunakan /gitlab untuk connect."

    async def _send(self, chat_id: int, text: str) -> None:
        await self._telegram.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    async def _send_reply(self, chat_id: int, reply: CallbackReply) -> None:
        await self._telegram.send_message(chat_id=chat_id, text=reply.text, parse_mode="HTML", reply_markup=reply.reply_markup)


def _command(text: str) -> tuple[str | None, str]:
    first, _, rest = text.partition(" ")
    if not first.startswith("/"):
        return None, text
    return first.split("@", 1)[0].lower(), rest.strip()
