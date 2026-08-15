from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.auth.models import ApplicationSessionModel
from app.platform.bots.models import TelegramBotModel
from app.platform.users.models import BotUserModel, BotUserStatus, TelegramUserModel


class ApplicationSessionRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        token_hash: str,
        user_id: int,
        launching_bot_id: int,
        now: datetime,
        expires_at: datetime,
    ) -> ApplicationSessionModel:
        model = ApplicationSessionModel(
            token_hash=token_hash,
            user_id=user_id,
            launching_bot_id=launching_bot_id,
            expires_at=expires_at,
            last_seen_at=now,
        )
        session.add(model)
        await session.flush()
        return model

    async def revoke_active_for_user_and_bot(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        launching_bot_id: int,
        now: datetime,
    ) -> None:
        await session.execute(
            update(ApplicationSessionModel)
            .where(
                ApplicationSessionModel.user_id == user_id,
                ApplicationSessionModel.launching_bot_id == launching_bot_id,
                ApplicationSessionModel.revoked_at.is_(None),
                ApplicationSessionModel.expires_at > now,
            )
            .values(revoked_at=now)
        )

    async def find_active(
        self,
        session: AsyncSession,
        *,
        token_hash: str,
        now: datetime,
    ) -> tuple[ApplicationSessionModel, TelegramUserModel, TelegramBotModel] | None:
        row = await session.execute(
            select(ApplicationSessionModel, TelegramUserModel, TelegramBotModel)
            .join(
                TelegramUserModel,
                TelegramUserModel.id == ApplicationSessionModel.user_id,
            )
            .join(
                TelegramBotModel,
                TelegramBotModel.id == ApplicationSessionModel.launching_bot_id,
            )
            .join(
                BotUserModel,
                BotUserModel.bot_id == ApplicationSessionModel.launching_bot_id,
            )
            .where(
                ApplicationSessionModel.token_hash == token_hash,
                ApplicationSessionModel.revoked_at.is_(None),
                ApplicationSessionModel.expires_at > now,
                TelegramBotModel.enabled.is_(True),
                BotUserModel.user_id == ApplicationSessionModel.user_id,
                BotUserModel.status == BotUserStatus.ACTIVE,
            )
            .with_for_update(of=ApplicationSessionModel)
        )
        return row.one_or_none()

    async def revoke_by_hash(
        self,
        session: AsyncSession,
        *,
        token_hash: str,
        now: datetime,
    ) -> bool:
        result = await session.execute(
            update(ApplicationSessionModel)
            .where(
                ApplicationSessionModel.token_hash == token_hash,
                ApplicationSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return result.rowcount == 1
