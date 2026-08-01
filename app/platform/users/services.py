from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.core.database import Database
from app.core.logging import get_logger
from app.platform.bots.schemas import BotRuntimeConfig
from app.platform.users.models import BotUserStateModel, BotUserStatus
from app.platform.users.repositories import (
    BotUserRepository,
    TelegramChatRepository,
    TelegramUserRepository,
    UserStateRepository,
)
from app.platform.users.schemas import BotUserPublic, UserStateValue
from app.shared.exceptions import UserBlockedError, UserStateConflictError
from app.shared.types import BotContext, ChatContext, SessionState, TelegramUpdate, UserContext

logger = get_logger(__name__)


class UserContextService:
    def __init__(
        self,
        database: Database,
        users: TelegramUserRepository,
        chats: TelegramChatRepository,
        bot_users: BotUserRepository,
        states: UserStateRepository,
    ) -> None:
        self._database = database
        self._users = users
        self._chats = chats
        self._bot_users = bot_users
        self._states = states

    @classmethod
    def build(cls, database: Database) -> UserContextService:
        return cls(
            database,
            TelegramUserRepository(),
            TelegramChatRepository(),
            BotUserRepository(),
            UserStateRepository(),
        )

    async def resolve(
        self, bot: BotRuntimeConfig, update: TelegramUpdate
    ) -> BotContext | None:
        telegram_user = update.effective_user()
        telegram_chat = update.effective_chat()
        if telegram_chat is None:
            return None

        blocked = False
        resolved_context: BotContext
        async with self._database.transaction() as session:
            chat = await self._chats.upsert(session, telegram_chat)
            if telegram_user is None:
                return ChatContext(
                    bot_id=bot.id,
                    bot_name=bot.name,
                    chat_id=chat.telegram_chat_id,
                    chat_type=chat.type,
                    chat_title=chat.title,
                    chat_username=chat.username,
                )

            user, user_created = await self._users.upsert(session, telegram_user)
            bot_user, relationship_created = await self._bot_users.resolve(
                session,
                bot_id=bot.id,
                user_id=user.id,
                locale=telegram_user.language_code,
            )
            blocked = bot_user.status in (
                BotUserStatus.BLOCKED,
                BotUserStatus.DISABLED,
            )
            state = await self._states.get_or_create(session, bot_user.id)

            if user_created:
                await logger.ainfo(
                    "telegram_user_registered",
                    internal_user_id=user.id,
                    telegram_user_id=user.telegram_user_id,
                )
            else:
                await logger.ainfo(
                    "telegram_user_profile_synchronized",
                    internal_user_id=user.id,
                    telegram_user_id=user.telegram_user_id,
                )
            if relationship_created:
                await logger.ainfo(
                    "bot_user_relationship_created",
                    bot_id=bot.id,
                    bot_user_id=bot_user.id,
                    internal_user_id=user.id,
                )

            resolved_context = UserContext(
                bot_id=bot.id,
                bot_name=bot.name,
                telegram_user_id=user.telegram_user_id,
                internal_user_id=user.id,
                bot_user_id=bot_user.id,
                chat_id=chat.telegram_chat_id,
                chat_type=chat.type,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                user_status=bot_user.status.value,
                user_role=bot_user.role,
                session_state=SessionState.immutable(
                    state=state.state, data=state.data, version=state.version
                ),
            )
        if blocked:
            await logger.awarning(
                "blocked_user_rejected",
                bot_id=bot.id,
                bot_name=bot.name,
                internal_user_id=resolved_context.internal_user_id,
                telegram_user_id=resolved_context.telegram_user_id,
                bot_user_id=resolved_context.bot_user_id,
                chat_id=resolved_context.chat_id,
            )
            raise UserBlockedError
        return resolved_context


class UserStateService:
    def __init__(
        self,
        database: Database,
        repository: UserStateRepository,
        conflict_retries: int,
    ) -> None:
        self._database = database
        self._repository = repository
        self._conflict_retries = conflict_retries

    async def get_state(self, bot_user_id: int) -> UserStateValue:
        async with self._database.transaction() as session:
            model = await self._repository.get_or_create(session, bot_user_id)
            return self._value(model)

    async def set_state(
        self,
        bot_user_id: int,
        *,
        state: str | None,
        data: dict[str, Any],
        expected_version: int,
        expires_at: datetime | None = None,
    ) -> UserStateValue:
        async with self._database.transaction() as session:
            model = await self._repository.compare_and_swap(
                session,
                bot_user_id=bot_user_id,
                expected_version=expected_version,
                state=state,
                data=data,
                expires_at=expires_at,
            )
            if model is None:
                raise UserStateConflictError
            await logger.ainfo(
                "user_state_changed",
                bot_user_id=bot_user_id,
                state=state,
                version=model.version,
            )
            return self._value(model)

    async def update_state(
        self,
        bot_user_id: int,
        mutate: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> UserStateValue:
        for _ in range(self._conflict_retries):
            current = await self.get_state(bot_user_id)
            new_data = mutate(dict(current.data))
            try:
                return await self.set_state(
                    bot_user_id,
                    state=current.state,
                    data=new_data,
                    expected_version=current.version,
                )
            except UserStateConflictError:
                continue
        raise UserStateConflictError

    async def clear_state(self, bot_user_id: int) -> UserStateValue:
        for _ in range(self._conflict_retries):
            current = await self.get_state(bot_user_id)
            try:
                return await self.set_state(
                    bot_user_id,
                    state=None,
                    data={},
                    expected_version=current.version,
                )
            except UserStateConflictError:
                continue
        raise UserStateConflictError

    @staticmethod
    def _value(model: BotUserStateModel) -> UserStateValue:
        return UserStateValue(
            state=model.state, data=dict(model.data), version=model.version
        )


class UserManagementService:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._users = TelegramUserRepository()
        self._bot_users = BotUserRepository()
        self._states = UserStateRepository()

    async def list_users(
        self, bot_id: int, *, limit: int = 100, offset: int = 0
    ) -> list[BotUserPublic]:
        async with self._database.session() as session:
            rows = await self._bot_users.list_by_bot(
                session, bot_id, limit=min(limit, 500), offset=max(offset, 0)
            )
            return [BotUserPublic.model_validate(row) for row in rows]

    async def set_status(
        self, bot_user_id: int, status: BotUserStatus
    ) -> BotUserPublic:
        async with self._database.transaction() as session:
            model = await self._bot_users.get(session, bot_user_id)
            if model is None:
                raise UserBlockedError("Bot user was not found.")
            model.status = status
            await session.flush()
            return BotUserPublic.model_validate(model)

    async def block(self, bot_user_id: int) -> BotUserPublic:
        return await self.set_status(bot_user_id, BotUserStatus.BLOCKED)

    async def unblock(self, bot_user_id: int) -> BotUserPublic:
        return await self.set_status(bot_user_id, BotUserStatus.ACTIVE)

    async def set_role(self, bot_user_id: int, role: str) -> BotUserPublic:
        async with self._database.transaction() as session:
            model = await self._bot_users.get(session, bot_user_id)
            if model is None:
                raise UserBlockedError("Bot user was not found.")
            model.role = role
            await session.flush()
            return BotUserPublic.model_validate(model)

    async def update_metadata(
        self, bot_user_id: int, metadata: dict[str, Any]
    ) -> BotUserPublic:
        async with self._database.transaction() as session:
            model = await self._bot_users.get(session, bot_user_id)
            if model is None:
                raise UserBlockedError("Bot user was not found.")
            model.metadata_ = dict(metadata)
            await session.flush()
            return BotUserPublic.model_validate(model)

    async def find_user(
        self, *, bot_id: int, telegram_user_id: int
    ) -> BotUserPublic | None:
        async with self._database.session() as session:
            user = await self._users.find_by_telegram_id(session, telegram_user_id)
            if user is None:
                return None
            bot_user = await self._bot_users.get_for_bot_and_user(
                session, bot_id=bot_id, user_id=user.id
            )
            return (
                BotUserPublic.model_validate(bot_user)
                if bot_user is not None
                else None
            )

    async def get_metadata(self, bot_user_id: int) -> dict[str, Any]:
        async with self._database.session() as session:
            model = await self._bot_users.get(session, bot_user_id)
            if model is None:
                raise UserBlockedError("Bot user was not found.")
            return dict(model.metadata_)

    async def clear_state(self, bot_user_id: int, conflict_retries: int = 5) -> None:
        state_service = UserStateService(
            self._database, self._states, conflict_retries
        )
        await state_service.clear_state(bot_user_id)
