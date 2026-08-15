from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import (
    FinanceBudgetPeriodModel,
    FinanceProfileModel,
    FinanceTransactionModel,
)
from app.platform.users.models import BotUserModel


class FinanceRepository:
    async def get_profile(
        self, session: AsyncSession, bot_user_id: int, *, for_update: bool = False
    ) -> FinanceProfileModel | None:
        statement = select(FinanceProfileModel).where(
            FinanceProfileModel.bot_user_id == bot_user_id
        )
        if for_update:
            statement = statement.with_for_update(of=FinanceProfileModel)
        return await session.scalar(statement)

    async def get_profile_by_id(
        self, session: AsyncSession, profile_id: int, *, for_update: bool = False
    ) -> FinanceProfileModel | None:
        statement = select(FinanceProfileModel).where(
            FinanceProfileModel.id == profile_id
        )
        if for_update:
            statement = statement.with_for_update(of=FinanceProfileModel)
        return await session.scalar(statement)

    async def create_profile(
        self,
        session: AsyncSession,
        *,
        bot_user_id: int,
        base_budget: int,
        recurring_days: int,
        alert_chat_id: int,
    ) -> FinanceProfileModel:
        model = FinanceProfileModel(
            bot_user_id=bot_user_id,
            base_budget=base_budget,
            recurring_days=recurring_days,
            timezone="Asia/Jakarta",
            alert_enabled=True,
            alert_chat_id=alert_chat_id,
        )
        session.add(model)
        await session.flush()
        return model

    async def list_profile_ids(
        self, session: AsyncSession, bot_id: int
    ) -> Sequence[int]:
        result = await session.scalars(
            select(FinanceProfileModel.id)
            .join(BotUserModel, BotUserModel.id == FinanceProfileModel.bot_user_id)
            .where(BotUserModel.bot_id == bot_id)
            .order_by(FinanceProfileModel.id)
        )
        return result.all()

    async def latest_period(
        self, session: AsyncSession, profile_id: int, *, for_update: bool = False
    ) -> FinanceBudgetPeriodModel | None:
        statement = (
            select(FinanceBudgetPeriodModel)
            .where(FinanceBudgetPeriodModel.profile_id == profile_id)
            .order_by(FinanceBudgetPeriodModel.sequence.desc())
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update(of=FinanceBudgetPeriodModel)
        return await session.scalar(statement)

    async def create_period(
        self,
        session: AsyncSession,
        **values: object,
    ) -> FinanceBudgetPeriodModel:
        model = FinanceBudgetPeriodModel(**values)
        session.add(model)
        await session.flush()
        return model

    async def realization(self, session: AsyncSession, period_id: int) -> int:
        value = await session.scalar(
            select(func.coalesce(func.sum(FinanceTransactionModel.amount), 0)).where(
                FinanceTransactionModel.period_id == period_id
            )
        )
        return int(value or 0)

    async def get_period_for_user(
        self,
        session: AsyncSession,
        *,
        bot_user_id: int,
        period_id: int,
        for_update: bool = False,
    ) -> FinanceBudgetPeriodModel | None:
        statement = (
            select(FinanceBudgetPeriodModel)
            .join(
                FinanceProfileModel,
                FinanceProfileModel.id == FinanceBudgetPeriodModel.profile_id,
            )
            .where(
                FinanceBudgetPeriodModel.id == period_id,
                FinanceProfileModel.bot_user_id == bot_user_id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=FinanceBudgetPeriodModel)
        return await session.scalar(statement)

    async def list_periods(
        self, session: AsyncSession, profile_id: int, *, limit: int
    ) -> Sequence[FinanceBudgetPeriodModel]:
        result = await session.scalars(
            select(FinanceBudgetPeriodModel)
            .where(FinanceBudgetPeriodModel.profile_id == profile_id)
            .order_by(FinanceBudgetPeriodModel.sequence.desc())
            .limit(limit)
        )
        return result.all()

    async def create_transaction(
        self,
        session: AsyncSession,
        *,
        profile_id: int,
        period_id: int,
        source_update_id: int,
        amount: int,
        purpose: str,
        spent_on: date,
    ) -> FinanceTransactionModel:
        created = await session.scalar(
            insert(FinanceTransactionModel)
            .values(
                profile_id=profile_id,
                period_id=period_id,
                source_update_id=source_update_id,
                amount=amount,
                purpose=purpose,
                spent_on=spent_on,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    FinanceTransactionModel.profile_id,
                    FinanceTransactionModel.source_update_id,
                ]
            )
            .returning(FinanceTransactionModel)
        )
        if created is not None:
            return created
        existing = await session.scalar(
            select(FinanceTransactionModel).where(
                FinanceTransactionModel.profile_id == profile_id,
                FinanceTransactionModel.source_update_id == source_update_id,
            )
        )
        if existing is None:
            raise RuntimeError("Transaction upsert did not return a row")
        return existing

    async def list_transactions(
        self, session: AsyncSession, period_id: int
    ) -> Sequence[FinanceTransactionModel]:
        result = await session.scalars(
            select(FinanceTransactionModel)
            .where(FinanceTransactionModel.period_id == period_id)
            .order_by(
                FinanceTransactionModel.spent_on,
                FinanceTransactionModel.id,
            )
        )
        return result.all()

    async def get_transaction_for_user(
        self,
        session: AsyncSession,
        *,
        bot_user_id: int,
        transaction_id: int,
        for_update: bool = False,
    ) -> tuple[FinanceTransactionModel, FinanceBudgetPeriodModel, FinanceProfileModel] | None:
        statement = (
            select(
                FinanceTransactionModel,
                FinanceBudgetPeriodModel,
                FinanceProfileModel,
            )
            .join(
                FinanceBudgetPeriodModel,
                FinanceBudgetPeriodModel.id == FinanceTransactionModel.period_id,
            )
            .join(
                FinanceProfileModel,
                FinanceProfileModel.id == FinanceTransactionModel.profile_id,
            )
            .where(
                FinanceTransactionModel.id == transaction_id,
                FinanceProfileModel.bot_user_id == bot_user_id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=FinanceTransactionModel)
        row = (await session.execute(statement)).one_or_none()
        return tuple(row) if row is not None else None  # type: ignore[return-value]

    async def delete_transaction(
        self, session: AsyncSession, transaction_id: int
    ) -> None:
        await session.execute(
            delete(FinanceTransactionModel).where(
                FinanceTransactionModel.id == transaction_id
            )
        )
