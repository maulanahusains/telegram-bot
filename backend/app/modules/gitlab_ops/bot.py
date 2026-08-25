from __future__ import annotations

from app.core.registry import BaseBot
from app.core.telegram_client import TelegramBotClient
from app.modules.gitlab_ops.router import GitlabOpsRouter
from app.modules.gitlab_ops.services import GitlabEventExecutor, GitlabOpsService
from app.shared.types import ChatContext, TelegramUpdate, UserContext


class GitlabOpsBot(BaseBot):
    def __init__(self, *, router: GitlabOpsRouter, service: GitlabOpsService, telegram: TelegramBotClient, executor_enabled: bool, executor_interval_seconds: int, executor_batch_size: int) -> None:
        self._router = router
        self._service = service
        self._telegram = telegram
        self._executor = GitlabEventExecutor(service, telegram, enabled=executor_enabled, interval_seconds=executor_interval_seconds, batch_size=executor_batch_size)

    @property
    def service(self) -> GitlabOpsService:
        return self._service

    async def start(self) -> None:
        await self._telegram.set_my_commands([
            {"command": "gitlab", "description": "Setup dan selector operasi GitLab"},
            {"command": "projects", "description": "Lihat project aktif dan statusnya"},
            {"command": "deploy", "description": "Pilih project dan promotion rule"},
            {"command": "mr", "description": "Lihat merge request"},
            {"command": "pipeline", "description": "Lihat pipeline terbaru"},
        ])
        await self._executor.start()

    async def stop(self) -> None:
        await self._executor.stop()

    async def handle_update(self, update: TelegramUpdate, context: UserContext | ChatContext) -> None:
        if isinstance(context, ChatContext) or update.edited_message is not None:
            return
        if context.chat_type not in ("private", "group", "supergroup"):
            return
        await self._router.dispatch(update, context)
