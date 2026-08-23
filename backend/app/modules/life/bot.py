from __future__ import annotations

from app.core.registry import BaseBot, BotDependencies
from app.core.telegram_client import SentMessage
from app.modules.life.services import LifeReminderExecutor, LifeService, ReminderDeliveryClaim
from app.platform.bots.schemas import BotRuntimeConfig
from app.shared.exceptions import LifeNotFoundError, LifeValidationError
from app.shared.types import BotContext, TelegramUpdate, UserContext


class LifeBot(BaseBot):
    """Life Telegram adapter: entry, candidate observation, and quick actions."""

    def __init__(self, config: BotRuntimeConfig, dependencies: BotDependencies) -> None:
        self.config = config
        self.dependencies = dependencies
        self.service = LifeService(dependencies.database, dependencies.settings)
        self._executor = LifeReminderExecutor(bot_id=config.id, service=self.service, deliver=self._deliver_reminder)

    async def start(self) -> None:
        await self.dependencies.telegram.set_my_commands(
            [
                {"command": "start", "description": "Open Life"},
                {"command": "app", "description": "Open the Life app"},
            ]
        )
        if self.dependencies.settings.life_reminder_executor_enabled:
            await self._executor.start()

    async def stop(self) -> None:
        await self._executor.stop()

    async def handle_update(self, update: TelegramUpdate, context: BotContext) -> None:
        if isinstance(context, UserContext):
            await self.service.record_destination_candidate(context)
        if update.callback_query is not None and isinstance(context, UserContext):
            await self._handle_callback(update, context)
            return
        message = update.effective_message()
        if message is None or message.text is None:
            return
        command = message.text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        if command == "/start":
            await self.dependencies.telegram.send_message(
                chat_id=message.chat.id,
                text="Life is ready. Open the app to manage your profile, destinations, and Planner reminders.",
                reply_markup=self._open_app_markup(message.chat.type),
            )
        elif command == "/app":
            await self.dependencies.telegram.send_message(
                chat_id=message.chat.id,
                text="Open Life.",
                reply_markup=self._open_app_markup(message.chat.type),
            )

    async def _deliver_reminder(self, claim: ReminderDeliveryClaim) -> SentMessage:
        if claim.chat_type in {"group", "supergroup"}:
            text = "Life reminder\nAction needed."
        elif claim.kind == "grocery":
            text = f"{claim.title}\n\n{claim.notes or 'Please check your grocery list in Life.'}"
        elif claim.kind == "goal_recommendation":
            text = f"{claim.title}\n\n{claim.notes or 'Review your calorie recommendation in Life.'}"
        else:
            text = f"{claim.title}\n\n{claim.notes or 'Reminder due.'}"
        if claim.kind == "grocery":
            reply_markup = {"inline_keyboard": [[self._open_app_button(claim.chat_type)]]}
        elif claim.kind == "goal_recommendation" and claim.goal_recommendation_id is not None and claim.chat_type == "private":
            recommendation_id = claim.goal_recommendation_id
            apply_label = f"Apply {claim.goal_recommendation_recommended_kcal:,} kcal" if claim.goal_recommendation_recommended_kcal is not None else "Apply"
            keep_label = f"Tetap {claim.goal_recommendation_current_kcal:,} kcal" if claim.goal_recommendation_current_kcal is not None else "Tetap"
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": apply_label, "callback_data": f"life:goal-rec:{recommendation_id}:apply"},
                        {"text": keep_label, "callback_data": f"life:goal-rec:{recommendation_id}:dismiss"},
                    ],
                    [{**self._open_app_button("private"), "text": "Lihat detail"}],
                ]
            }
        else:
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "Done", "callback_data": f"life:occurrence:{claim.occurrence_id}:completed"},
                        {"text": "Skip", "callback_data": f"life:occurrence:{claim.occurrence_id}:skipped"},
                    ],
                    [self._open_app_button(claim.chat_type)],
                ]
            }
        return await self.dependencies.telegram.send_message(
            chat_id=claim.telegram_chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def _handle_callback(self, update: TelegramUpdate, context: UserContext) -> None:
        callback = update.callback_query
        assert callback is not None
        data = callback.data or ""
        parts = data.split(":")
        if len(parts) == 4 and parts[0] == "life" and parts[1] == "goal-rec" and parts[3] in {"apply", "dismiss"}:
            if context.chat_type != "private":
                await self.dependencies.telegram.answer_callback_query(
                    callback_query_id=callback.id,
                    text="Rekomendasi hanya dapat diproses di chat pribadi.",
                )
                return
            try:
                recommendation_id = int(parts[2])
                result = await self.service.transition_goal_recommendation(context.internal_user_id, recommendation_id, parts[3])
            except (ValueError, LifeNotFoundError, LifeValidationError):
                await self.dependencies.telegram.answer_callback_query(
                    callback_query_id=callback.id,
                    text="Hanya pemilik rekomendasi yang dapat memilih.",
                )
                return
            await self.dependencies.telegram.answer_callback_query(
                callback_query_id=callback.id,
                text=result.message,
            )
            if callback.message is not None:
                await self.dependencies.telegram.edit_message_reply_markup(
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                )
            return
        if len(parts) != 4 or parts[0] != "life" or parts[1] != "occurrence" or parts[3] not in {"completed", "skipped"}:
            return
        try:
            occurrence_id = int(parts[2])
            await self.service.transition_occurrence(context.internal_user_id, occurrence_id, parts[3])
        except (ValueError, LifeNotFoundError, LifeValidationError):
            await self.dependencies.telegram.answer_callback_query(
                callback_query_id=callback.id,
                text="Only the reminder owner can use this action.",
            )
            return
        await self.dependencies.telegram.answer_callback_query(
            callback_query_id=callback.id,
            text="Reminder updated.",
        )

    def _open_app_markup(self, chat_type: str) -> dict[str, object]:
        return {"inline_keyboard": [[self._open_app_button(chat_type)]]}

    def _open_app_button(self, chat_type: str) -> dict[str, object]:
        if chat_type == "private":
            return {"text": "Open Life", "web_app": {"url": self._app_url}}
        return {"text": "Open Life", "url": self._group_mini_app_url}

    @property
    def _app_url(self) -> str:
        return f"{self.dependencies.settings.webhook_base_url}/tg/{self.config.name}"

    @property
    def _group_mini_app_url(self) -> str:
        username = self.dependencies.telegram.identity.username if self.dependencies.telegram.identity else None
        if username:
            return f"https://t.me/{username}?startapp=life"
        # A healthy runtime has been through getMe before start; this fallback remains a non-sensitive link.
        return self._app_url


def create_life_bot(config: BotRuntimeConfig, dependencies: BotDependencies) -> LifeBot:
    return LifeBot(config, dependencies)
