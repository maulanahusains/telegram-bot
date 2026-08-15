from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.users.models import (
    BotUserModel,
    BotUserStateModel,
    BotUserStatus,
    TelegramChatModel,
    TelegramUserModel,
)
from app.shared.types import TelegramChat, TelegramUser


class TelegramUserRepository:
    async def find_by_telegram_id(
        self, session: AsyncSession, telegram_user_id: int
    ) -> TelegramUserModel | None:
        return await session.scalar(
            select(TelegramUserModel).where(
                TelegramUserModel.telegram_user_id == telegram_user_id
            )
        )

    async def upsert(
        self, session: AsyncSession, user: TelegramUser
    ) -> tuple[TelegramUserModel, bool]:
        created = await session.scalar(
            insert(TelegramUserModel)
            .values(
                telegram_user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_bot=user.is_bot,
            )
            .on_conflict_do_nothing(
                index_elements=[TelegramUserModel.telegram_user_id]
            )
            .returning(TelegramUserModel)
        )
        if created is not None:
            return created, True
        model = await session.scalar(
            select(TelegramUserModel)
            .where(TelegramUserModel.telegram_user_id == user.id)
            .with_for_update()
        )
        if model is None:
            raise RuntimeError("Telegram user upsert did not return a row")
        model.username = user.username
        model.first_name = user.first_name
        model.last_name = user.last_name
        model.language_code = user.language_code
        model.is_bot = user.is_bot
        model.last_seen_at = func.now()
        return model, False


class TelegramChatRepository:
    async def upsert(
        self, session: AsyncSession, chat: TelegramChat
    ) -> TelegramChatModel:
        statement = (
            insert(TelegramChatModel)
            .values(
                telegram_chat_id=chat.id,
                type=chat.type,
                title=chat.title,
                username=chat.username,
            )
            .on_conflict_do_update(
                index_elements=[TelegramChatModel.telegram_chat_id],
                set_={
                    "type": chat.type,
                    "title": chat.title,
                    "username": chat.username,
                    "last_seen_at": func.now(),
                },
            )
            .returning(TelegramChatModel)
        )
        return (await session.scalars(statement)).one()


class BotUserRepository:
    async def resolve(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        user_id: int,
        locale: str | None,
    ) -> tuple[BotUserModel, bool]:
        created = await session.scalar(
            insert(BotUserModel)
            .values(bot_id=bot_id, user_id=user_id, locale=locale)
            .on_conflict_do_nothing(
                index_elements=[BotUserModel.bot_id, BotUserModel.user_id]
            )
            .returning(BotUserModel)
        )
        if created is not None:
            return created, True
        model = await session.scalar(
            select(BotUserModel)
            .where(BotUserModel.bot_id == bot_id, BotUserModel.user_id == user_id)
            .with_for_update()
        )
        if model is None:
            raise RuntimeError("Bot-user upsert did not return a row")
        model.last_seen_at = func.now()
        if locale is not None:
            model.locale = locale
        return model, False

    async def list_by_bot(
        self, session: AsyncSession, bot_id: int, *, limit: int, offset: int
    ) -> Sequence[BotUserModel]:
        result = await session.scalars(
            select(BotUserModel)
            .where(BotUserModel.bot_id == bot_id)
            .order_by(BotUserModel.id)
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def get(self, session: AsyncSession, bot_user_id: int) -> BotUserModel | None:
        return await session.get(BotUserModel, bot_user_id)

    async def get_for_bot_and_user(
        self, session: AsyncSession, *, bot_id: int, user_id: int
    ) -> BotUserModel | None:
        return await session.scalar(
            select(BotUserModel).where(
                BotUserModel.bot_id == bot_id,
                BotUserModel.user_id == user_id,
            )
        )


class UserStateRepository:
    async def get_or_create(
        self, session: AsyncSession, bot_user_id: int
    ) -> BotUserStateModel:
        model = await session.scalar(
            insert(BotUserStateModel)
            .values(bot_user_id=bot_user_id, state=None, data={}, version=0)
            .on_conflict_do_nothing(index_elements=[BotUserStateModel.bot_user_id])
            .returning(BotUserStateModel)
        )
        if model is not None:
            return model
        existing = await session.scalar(
            select(BotUserStateModel).where(
                BotUserStateModel.bot_user_id == bot_user_id
            )
        )
        if existing is None:
            raise RuntimeError("Bot-user state upsert did not return a row")
        return existing

    async def compare_and_swap(
        self,
        session: AsyncSession,
        *,
        bot_user_id: int,
        expected_version: int,
        state: str | None,
        data: dict[str, Any],
        expires_at: datetime | None,
    ) -> BotUserStateModel | None:
        statement = (
            update(BotUserStateModel)
            .where(
                BotUserStateModel.bot_user_id == bot_user_id,
                BotUserStateModel.version == expected_version,
            )
            .values(
                state=state,
                data=data,
                expires_at=expires_at,
                version=BotUserStateModel.version + 1,
            )
            .returning(BotUserStateModel)
        )
        return await session.scalar(statement)
