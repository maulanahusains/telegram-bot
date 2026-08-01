from __future__ import annotations

from app.core.registry import BaseBot
from app.core.telegram_client import TelegramBotClient
from app.modules.finance.formatting import rollover_markup, summary_text
from app.modules.finance.router import FinanceRouter
from app.modules.finance.schemas import AlertClaim
from app.modules.finance.services import FinanceAlertScheduler
from app.shared.types import ChatContext, TelegramUpdate, UserContext


class FinanceBot(BaseBot):
    def __init__(
        self,
        router: FinanceRouter,
        scheduler: FinanceAlertScheduler,
        telegram: TelegramBotClient,
    ) -> None:
        self._router = router
        self._scheduler = scheduler
        self._telegram = telegram

    async def start(self) -> None:
        await self._scheduler.start()

    async def stop(self) -> None:
        await self._scheduler.stop()

    async def handle_update(
        self, update: TelegramUpdate, context: UserContext | ChatContext
    ) -> None:
        if isinstance(context, ChatContext) or update.edited_message is not None:
            return
        await self._router.dispatch(update, context)

    async def deliver_alert(self, claim: AlertClaim) -> None:
        markup = (
            rollover_markup(claim.period)
            if claim.period.effective_budget is None
            else None
        )
        await self._telegram.send_message(
            chat_id=claim.profile.alert_chat_id,
            text=summary_text(claim.period, today=claim.local_date),
            parse_mode="HTML",
            reply_markup=markup,
        )
