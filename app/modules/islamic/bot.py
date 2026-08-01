from __future__ import annotations

from html import escape

from app.core.registry import BaseBot
from app.core.telegram_client import TelegramBotClient
from app.modules.islamic.router import IslamicRouter
from app.modules.islamic.schemas import PrayerClaim
from app.modules.islamic.services import IslamicScheduler, IslamicService
from app.shared.types import ChatContext, TelegramUpdate, UserContext


class IslamicBot(BaseBot):
    def __init__(
        self,
        router: IslamicRouter,
        service: IslamicService,
        scheduler: IslamicScheduler,
        telegram: TelegramBotClient,
    ) -> None:
        self._router = router
        self._service = service
        self._scheduler = scheduler
        self._telegram = telegram

    async def start(self) -> None:
        await self._telegram.set_my_commands(
            [
                {"command": "setup", "description": "Atur lokasi dan jadwal adzan"},
                {"command": "quran", "description": "Atur posisi terakhir Quran"},
                {"command": "read", "description": "Mulai sesi baca Quran"},
                {"command": "stats", "description": "Lihat statistik Quran chat ini"},
                {"command": "help", "description": "Lihat panduan bot"},
            ]
        )
        await self._scheduler.start()

    async def stop(self) -> None:
        await self._scheduler.stop()

    async def handle_update(
        self, update: TelegramUpdate, context: UserContext | ChatContext
    ) -> None:
        if isinstance(context, ChatContext) or update.edited_message is not None:
            return
        if context.chat_type not in ("private", "group", "supergroup"):
            return
        await self._router.dispatch(update, context)

    async def deliver_reminder(self, claim: PrayerClaim) -> None:
        if claim.skip_message:
            if claim.old_message_id is not None:
                await self.cleanup_messages(claim.chat_id, [claim.old_message_id])
            await self._service.complete_prayer_claim(claim, None)
            return
        if claim.kind == "pre":
            text = f"Adzan {escape(claim.prayer_name)} dalam 15 menit"
        elif claim.kind == "adhan":
            text = (
                f"Adzan {escape(claim.prayer_name)} telah tiba, "
                "semoga Allah mengampuni kita semua"
            )
        else:
            progress = await self._service.progress(claim.scope_id)
            if progress.last_ayah_number == 0:
                text = "Yuk mulai membaca Quran. Gunakan /quran untuk mengatur posisi awal."
            else:
                text = (
                    "Waktunya membaca Quran.\n"
                    f"Terakhir: <b>{escape(str(progress.last_surah_name))} "
                    f"{progress.last_surah_number}:{progress.last_ayah_in_surah}</b>, "
                    f"halaman {progress.last_page}.\n"
                    "Lanjutkan dengan /read 1p atau /read 5a."
                )
        sent = await self._telegram.send_message(
            chat_id=claim.chat_id, text=text, parse_mode="HTML"
        )
        await self._service.complete_prayer_claim(claim, sent.message_id)
        if claim.old_message_id is not None and claim.old_message_id != sent.message_id:
            await self.cleanup_messages(claim.chat_id, [claim.old_message_id])

    async def cleanup_messages(self, chat_id: int, message_ids: list[int]) -> None:
        for message_id in dict.fromkeys(message_ids):
            try:
                await self._telegram.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
