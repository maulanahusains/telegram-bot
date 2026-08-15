from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.bots.models import TelegramBotModel


class BotRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        module_name: str,
        token_ciphertext: str,
        secret_token_ciphertext: str,
        enabled: bool,
        description: str | None,
    ) -> TelegramBotModel:
        model = TelegramBotModel(
            name=name,
            module_name=module_name,
            token_ciphertext=token_ciphertext,
            secret_token_ciphertext=secret_token_ciphertext,
            enabled=enabled,
            description=description,
        )
        session.add(model)
        await session.flush()
        return model

    async def list_all(self, session: AsyncSession) -> Sequence[TelegramBotModel]:
        result = await session.scalars(
            select(TelegramBotModel).order_by(TelegramBotModel.name)
        )
        return result.all()

    async def get_by_name(
        self, session: AsyncSession, name: str
    ) -> TelegramBotModel | None:
        return await session.scalar(
            select(TelegramBotModel).where(TelegramBotModel.name == name)
        )

    async def upsert(
        self,
        session: AsyncSession,
        *,
        name: str,
        module_name: str,
        token_ciphertext: str,
        secret_token_ciphertext: str,
        enabled: bool,
        description: str | None,
    ) -> TelegramBotModel:
        statement = (
            insert(TelegramBotModel)
            .values(
                name=name,
                module_name=module_name,
                token_ciphertext=token_ciphertext,
                secret_token_ciphertext=secret_token_ciphertext,
                enabled=enabled,
                description=description,
            )
            .on_conflict_do_update(
                index_elements=[TelegramBotModel.name],
                set_={
                    "module_name": module_name,
                    "token_ciphertext": token_ciphertext,
                    "secret_token_ciphertext": secret_token_ciphertext,
                    "enabled": enabled,
                    "description": description,
                    "webhook_sync_fingerprint": None,
                },
            )
            .returning(TelegramBotModel)
        )
        return (await session.scalars(statement)).one()

    async def set_enabled(
        self, session: AsyncSession, *, name: str, enabled: bool
    ) -> TelegramBotModel | None:
        model = await self.get_by_name(session, name)
        if model is None:
            return None
        model.enabled = enabled
        return model

    async def patch(
        self, session: AsyncSession, *, name: str, values: dict[str, object]
    ) -> TelegramBotModel | None:
        model = await self.get_by_name(session, name)
        if model is None:
            return None
        for field, value in values.items():
            setattr(model, field, value)
        if "token_ciphertext" in values or "secret_token_ciphertext" in values:
            model.webhook_sync_fingerprint = None
        return model

    async def record_webhook_sync(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        webhook_url: str,
        fingerprint: str,
    ) -> None:
        model = await session.get(TelegramBotModel, bot_id)
        if model is None:
            return
        from sqlalchemy import func

        model.webhook_url = webhook_url
        model.webhook_sync_fingerprint = fingerprint
        model.webhook_synced_at = func.now()
