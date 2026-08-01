from __future__ import annotations

from datetime import date
from html import escape

from app.core.telegram_client import TelegramBotClient
from app.modules.finance.formatting import (
    help_text,
    history_text,
    idr,
    rollover_markup,
    summary_text,
    transactions_text,
)
from app.modules.finance.parsing import (
    FinanceInputError,
    parse_amount,
    parse_setup,
    parse_shorthand,
    parse_spend,
)
from app.modules.finance.schemas import FinanceCommand, PeriodValue, SpendInput
from app.modules.finance.services import FinanceService
from app.shared.types import TelegramCallbackQuery, TelegramUpdate, UserContext


class FinanceRouter:
    def __init__(
        self, service: FinanceService, telegram: TelegramBotClient
    ) -> None:
        self._service = service
        self._telegram = telegram

    async def dispatch(self, update: TelegramUpdate, context: UserContext) -> None:
        if update.callback_query is not None:
            await self._handle_callback(update.callback_query, context)
            return
        message = update.effective_message()
        if message is None or message.text is None:
            return
        text = message.text.strip()
        if not text:
            return
        first, _, arguments = text.partition(" ")
        command = first.lower().split("@", 1)[0]
        try:
            if command in (FinanceCommand.START, FinanceCommand.HELP):
                await self._send(context.chat_id, help_text())
            elif command == FinanceCommand.SETUP:
                today = await self._service.local_today(context.bot_user_id)
                period = await self._service.setup(
                    context.bot_user_id,
                    context.chat_id,
                    parse_setup(arguments, today=today),
                )
                await self._send(
                    context.chat_id,
                    summary_text(period, today=today)
                    + "\n\nAlert aktif pukul 08:00 Asia/Jakarta di chat ini.",
                )
            elif command == FinanceCommand.BUDGET:
                amount = parse_amount(arguments, allow_zero=True)
                period = await self._service.update_budget(
                    context.bot_user_id, amount
                )
                today = await self._service.local_today(context.bot_user_id)
                await self._send(
                    context.chat_id, summary_text(period, today=today)
                )
            elif command == FinanceCommand.SPEND:
                await self._record(
                    context, update.update_id, parse_spend(arguments)
                )
            elif command == FinanceCommand.TRANSACTIONS:
                period_id = self._optional_positive_int(arguments, "ID periode")
                period, transactions = await self._service.list_transactions(
                    context.bot_user_id, period_id
                )
                await self._send(
                    context.chat_id, transactions_text(period, transactions)
                )
            elif command == FinanceCommand.EDIT:
                transaction_id, spend = self._parse_edit(arguments)
                transaction = await self._service.edit_transaction(
                    context.bot_user_id, transaction_id, spend
                )
                await self._send(
                    context.chat_id,
                    f"Transaksi #{transaction.id} diperbarui.\n"
                    f"{idr(transaction.amount)} · {escape(transaction.purpose)}\n"
                    f"Tanggal: {transaction.spent_on:%d-%m-%Y}",
                )
            elif command == FinanceCommand.DELETE:
                transaction_id = self._required_positive_int(
                    arguments, "Gunakan /delete <ID transaksi>."
                )
                transaction = await self._service.transaction_for_delete(
                    context.bot_user_id, transaction_id
                )
                await self._telegram.send_message(
                    chat_id=context.chat_id,
                    parse_mode="HTML",
                    text=(
                        f"Hapus transaksi #{transaction.id}?\n"
                        f"{idr(transaction.amount)} · {escape(transaction.purpose)}"
                    ),
                    reply_markup={
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Hapus",
                                    "callback_data": f"fin:del:{transaction.id}:yes",
                                },
                                {
                                    "text": "Batal",
                                    "callback_data": f"fin:del:{transaction.id}:no",
                                },
                            ]
                        ]
                    },
                )
            elif command == FinanceCommand.SUMMARY:
                period_id = self._optional_positive_int(arguments, "ID periode")
                period = await self._service.period_summary(
                    context.bot_user_id, period_id
                )
                today = await self._service.local_today(context.bot_user_id)
                await self._send_period(context.chat_id, period, today)
            elif command == FinanceCommand.HISTORY:
                limit = self._optional_positive_int(arguments, "Jumlah periode") or 8
                periods = await self._service.history(context.bot_user_id, limit)
                today = await self._service.local_today(context.bot_user_id)
                await self._send(
                    context.chat_id, history_text(periods, today=today)
                )
            elif command == FinanceCommand.ALERT:
                if not arguments.strip():
                    profile = await self._service.profile(context.bot_user_id)
                else:
                    profile = await self._service.set_alert(
                        context.bot_user_id, arguments, context.chat_id
                    )
                status = "aktif" if profile.alert_enabled else "nonaktif"
                await self._send(
                    context.chat_id,
                    f"Alert {status}.\n"
                    f"Jam: {profile.alert_time:%H:%M}\n"
                    f"Timezone: {escape(profile.timezone)}\n"
                    f"Chat tujuan: <code>{profile.alert_chat_id}</code>",
                )
            elif command == FinanceCommand.TIMEZONE:
                timezone = arguments.strip()
                if not timezone:
                    raise FinanceInputError(
                        "Gunakan /timezone Asia/Jakarta atau timezone IANA lain."
                    )
                profile = await self._service.set_timezone(
                    context.bot_user_id, timezone
                )
                await self._send(
                    context.chat_id,
                    f"Timezone diubah ke <code>{escape(profile.timezone)}</code>.",
                )
            elif command == FinanceCommand.CANCEL:
                await self._send(context.chat_id, "Tidak ada proses bertahap yang aktif.")
            elif command.startswith("/"):
                await self._send(
                    context.chat_id,
                    "Command tidak dikenali. Gunakan /help untuk melihat panduan.",
                )
            else:
                shorthand = parse_shorthand(text)
                if shorthand is None:
                    await self._send(
                        context.chat_id,
                        "Format tidak dikenali. Contoh: <code>50rb makan siang</code>.",
                    )
                else:
                    await self._record(context, update.update_id, shorthand)
        except FinanceInputError as error:
            await self._send(context.chat_id, escape(str(error)))

    async def _record(
        self, context: UserContext, update_id: int, data: SpendInput
    ) -> None:
        transaction = await self._service.record_transaction(
            context.bot_user_id, update_id, data
        )
        period = await self._service.current_period(context.bot_user_id)
        today = await self._service.local_today(context.bot_user_id)
        receipt = (
            f"Tercatat #{transaction.id}\n"
            f"{idr(transaction.amount)} · {escape(transaction.purpose)}\n"
            f"Tanggal: {transaction.spent_on:%d-%m-%Y}\n\n"
        )
        await self._send_period(
            context.chat_id, period, today, prefix=receipt
        )

    async def _handle_callback(
        self, callback: TelegramCallbackQuery, context: UserContext
    ) -> None:
        data = callback.data or ""
        try:
            parts = data.split(":")
            if len(parts) != 4 or parts[0] != "fin":
                await self._telegram.answer_callback_query(
                    callback_query_id=callback.id, text="Aksi tidak dikenali."
                )
                return
            action, raw_id, choice = parts[1], parts[2], parts[3]
            item_id = self._required_positive_int(raw_id, "ID callback tidak valid.")
            if action == "roll":
                period = await self._service.resolve_rollover(
                    context.bot_user_id, item_id, choice
                )
                today = await self._service.local_today(context.bot_user_id)
                text = summary_text(period, today=today)
                await self._telegram.answer_callback_query(
                    callback_query_id=callback.id, text="Rollover disimpan."
                )
            elif action == "del" and choice in ("yes", "no"):
                if choice == "yes":
                    await self._service.delete_transaction(
                        context.bot_user_id, item_id
                    )
                    text = f"Transaksi #{item_id} dihapus."
                else:
                    await self._service.transaction_for_delete(
                        context.bot_user_id, item_id
                    )
                    text = f"Penghapusan transaksi #{item_id} dibatalkan."
                await self._telegram.answer_callback_query(
                    callback_query_id=callback.id, text="Selesai."
                )
            else:
                raise FinanceInputError("Aksi tidak dikenali.")
            if callback.message is not None:
                await self._telegram.edit_message(
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup={"inline_keyboard": []},
                )
        except FinanceInputError as error:
            await self._telegram.answer_callback_query(
                callback_query_id=callback.id, text=str(error)[:180]
            )

    async def _send_period(
        self,
        chat_id: int,
        period: PeriodValue,
        today: date,
        *,
        prefix: str = "",
    ) -> None:
        markup = rollover_markup(period) if period.effective_budget is None else None
        await self._telegram.send_message(
            chat_id=chat_id,
            text=prefix + summary_text(period, today=today),
            parse_mode="HTML",
            reply_markup=markup,
        )

    async def _send(self, chat_id: int, text: str) -> None:
        chunks: list[str] = []
        current = ""
        for line in text.splitlines(keepends=True):
            if current and len(current) + len(line) > 3900:
                chunks.append(current.rstrip())
                current = ""
            current += line
        if current:
            chunks.append(current.rstrip())
        for chunk in chunks or [text]:
            await self._telegram.send_message(
                chat_id=chat_id, text=chunk, parse_mode="HTML"
            )

    @staticmethod
    def _parse_edit(arguments: str) -> tuple[int, SpendInput]:
        raw_id, separator, remainder = arguments.strip().partition(" ")
        if not separator:
            raise FinanceInputError(
                "Gunakan /edit <ID> <nominal> <untuk apa> [date=YYYY-MM-DD]."
            )
        transaction_id = FinanceRouter._required_positive_int(
            raw_id, "ID transaksi tidak valid."
        )
        return transaction_id, parse_spend(remainder)

    @staticmethod
    def _optional_positive_int(value: str, label: str) -> int | None:
        if not value.strip():
            return None
        return FinanceRouter._required_positive_int(
            value.strip(), f"{label} harus berupa angka positif."
        )

    @staticmethod
    def _required_positive_int(value: str, message: str) -> int:
        try:
            result = int(value.strip())
        except ValueError as error:
            raise FinanceInputError(message) from error
        if result <= 0:
            raise FinanceInputError(message)
        return result
