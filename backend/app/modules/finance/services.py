from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.core.logging import get_logger
from app.modules.finance.models import (
    FinanceBudgetPeriodModel,
    FinanceProfileModel,
    FinanceTransactionModel,
    RolloverStatus,
)
from app.modules.finance.parsing import FinanceInputError
from app.modules.finance.repositories import FinanceRepository
from app.modules.finance.schemas import (
    AlertClaim,
    PeriodValue,
    ProfileValue,
    SetupInput,
    SpendInput,
    TransactionValue,
)
from app.shared.utils import utc_now

logger = get_logger(__name__)


class FinanceService:
    def __init__(
        self, database: Database, repository: FinanceRepository, bot_id: int
    ) -> None:
        self._database = database
        self._repository = repository
        self._bot_id = bot_id

    async def local_today(self, bot_user_id: int) -> date:
        async with self._database.session() as session:
            profile = await self._repository.get_profile(session, bot_user_id)
        timezone = profile.timezone if profile is not None else "Asia/Jakarta"
        return datetime.now(ZoneInfo(timezone)).date()

    async def setup(
        self, bot_user_id: int, chat_id: int, data: SetupInput
    ) -> PeriodValue:
        try:
            async with self._database.transaction() as session:
                existing = await self._repository.get_profile(session, bot_user_id)
                if existing is not None:
                    raise FinanceInputError(
                        "Finance sudah disiapkan. Gunakan /budget untuk mengubah nominal."
                    )
                profile = await self._repository.create_profile(
                    session,
                    bot_user_id=bot_user_id,
                    base_budget=data.amount,
                    recurring_days=data.recurring_days,
                    alert_chat_id=chat_id,
                )
                jakarta_now = datetime.now(ZoneInfo("Asia/Jakarta"))
                if jakarta_now.time().replace(tzinfo=None) >= profile.alert_time:
                    profile.last_alert_local_date = jakarta_now.date()
                period = await self._repository.create_period(
                    session,
                    profile_id=profile.id,
                    sequence=1,
                    start_date=data.start_date,
                    end_date=data.start_date + timedelta(days=data.first_days - 1),
                    base_budget=data.amount,
                    previous_balance=None,
                    applied_carry=0,
                    effective_budget=data.amount,
                    rollover_status=RolloverStatus.INITIAL.value,
                    rollover_decided_at=utc_now(),
                )
                return await self._period_value(session, period)
        except IntegrityError as error:
            raise FinanceInputError("Finance sudah disiapkan untuk user ini.") from error

    async def current_period(self, bot_user_id: int) -> PeriodValue:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.session() as session:
            period = await self._repository.latest_period(session, profile_id)
            if period is None:
                raise FinanceInputError("Periode budget belum tersedia.")
            return await self._period_value(session, period)

    async def update_budget(self, bot_user_id: int, amount: int) -> PeriodValue:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile_by_id(
                session, profile_id, for_update=True
            )
            period = await self._repository.latest_period(
                session, profile_id, for_update=True
            )
            if profile is None or period is None:
                raise FinanceInputError("Finance belum disiapkan.")
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            if today > period.end_date:
                raise FinanceInputError("Periode aktif sudah berakhir.")
            profile.base_budget = amount
            period.base_budget = amount
            period.effective_budget = amount
            period.applied_carry = 0
            period.rollover_status = RolloverStatus.CUSTOM.value
            period.rollover_decided_at = utc_now()
            return await self._period_value(session, period)

    async def record_transaction(
        self, bot_user_id: int, update_id: int, data: SpendInput
    ) -> TransactionValue:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile_by_id(
                session, profile_id, for_update=True
            )
            period = await self._repository.latest_period(
                session, profile_id, for_update=True
            )
            if profile is None or period is None:
                raise FinanceInputError("Finance belum disiapkan.")
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            spent_on = data.spent_on or today
            self._validate_transaction_date(spent_on, today, period.start_date, period.end_date)
            model = await self._repository.create_transaction(
                session,
                profile_id=profile.id,
                period_id=period.id,
                source_update_id=update_id,
                amount=data.amount,
                purpose=data.purpose,
                spent_on=spent_on,
            )
            return self._transaction_value(model)

    async def list_transactions(
        self, bot_user_id: int, period_id: int | None = None
    ) -> tuple[PeriodValue, list[TransactionValue]]:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.session() as session:
            if period_id is None:
                period = await self._repository.latest_period(session, profile_id)
            else:
                period = await self._repository.get_period_for_user(
                    session, bot_user_id=bot_user_id, period_id=period_id
                )
            if period is None:
                raise FinanceInputError("Periode tidak ditemukan.")
            models = await self._repository.list_transactions(session, period.id)
            value = await self._period_value(session, period)
            return value, [self._transaction_value(model) for model in models]

    async def edit_transaction(
        self, bot_user_id: int, transaction_id: int, data: SpendInput
    ) -> TransactionValue:
        async with self._database.transaction() as session:
            row = await self._repository.get_transaction_for_user(
                session,
                bot_user_id=bot_user_id,
                transaction_id=transaction_id,
                for_update=True,
            )
            if row is None:
                raise FinanceInputError("Transaksi tidak ditemukan.")
            transaction, period, profile = row
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            if period.end_date < today:
                raise FinanceInputError("Transaksi pada periode selesai tidak dapat diubah.")
            spent_on = data.spent_on or transaction.spent_on
            self._validate_transaction_date(spent_on, today, period.start_date, period.end_date)
            transaction.amount = data.amount
            transaction.purpose = data.purpose
            transaction.spent_on = spent_on
            await session.flush()
            return self._transaction_value(transaction)

    async def transaction_for_delete(
        self, bot_user_id: int, transaction_id: int
    ) -> TransactionValue:
        async with self._database.session() as session:
            row = await self._repository.get_transaction_for_user(
                session, bot_user_id=bot_user_id, transaction_id=transaction_id
            )
            if row is None:
                raise FinanceInputError("Transaksi tidak ditemukan.")
            transaction, period, profile = row
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            if period.end_date < today:
                raise FinanceInputError("Transaksi pada periode selesai tidak dapat dihapus.")
            return self._transaction_value(transaction)

    async def delete_transaction(
        self, bot_user_id: int, transaction_id: int
    ) -> None:
        async with self._database.transaction() as session:
            row = await self._repository.get_transaction_for_user(
                session,
                bot_user_id=bot_user_id,
                transaction_id=transaction_id,
                for_update=True,
            )
            if row is None:
                raise FinanceInputError("Transaksi tidak ditemukan atau sudah dihapus.")
            _transaction, period, profile = row
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            if period.end_date < today:
                raise FinanceInputError("Transaksi pada periode selesai tidak dapat dihapus.")
            await self._repository.delete_transaction(session, transaction_id)

    async def period_summary(
        self, bot_user_id: int, period_id: int | None = None
    ) -> PeriodValue:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.session() as session:
            if period_id is None:
                period = await self._repository.latest_period(session, profile_id)
            else:
                period = await self._repository.get_period_for_user(
                    session, bot_user_id=bot_user_id, period_id=period_id
                )
            if period is None:
                raise FinanceInputError("Periode tidak ditemukan.")
            return await self._period_value(session, period)

    async def history(self, bot_user_id: int, limit: int) -> list[PeriodValue]:
        profile_id = await self._profile_id(bot_user_id)
        await self._ensure_period(profile_id)
        async with self._database.session() as session:
            periods = await self._repository.list_periods(
                session, profile_id, limit=max(1, min(limit, 20))
            )
            return [await self._period_value(session, period) for period in periods]

    async def resolve_rollover(
        self, bot_user_id: int, period_id: int, choice: str
    ) -> PeriodValue:
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile(
                session, bot_user_id, for_update=True
            )
            period = await self._repository.get_period_for_user(
                session,
                bot_user_id=bot_user_id,
                period_id=period_id,
                for_update=True,
            )
            if period is None or profile is None:
                raise FinanceInputError("Periode rollover tidak ditemukan.")
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            if period.end_date < today:
                raise FinanceInputError("Keputusan rollover tersebut sudah kedaluwarsa.")
            if period.rollover_status != RolloverStatus.PENDING.value:
                raise FinanceInputError("Rollover periode ini sudah diputuskan.")
            balance = period.previous_balance or 0
            if choice == "carry":
                period.effective_budget = period.base_budget + balance
                period.applied_carry = balance
                period.rollover_status = RolloverStatus.CARRY.value
            elif choice == "base":
                period.effective_budget = period.base_budget
                period.applied_carry = 0
                period.rollover_status = RolloverStatus.BASE.value
            elif choice == "zero":
                period.effective_budget = 0
                period.applied_carry = -period.base_budget
                period.rollover_status = RolloverStatus.ZERO.value
            else:
                raise FinanceInputError("Pilihan rollover tidak valid.")
            period.rollover_decided_at = utc_now()
            return await self._period_value(session, period)

    async def set_alert(
        self, bot_user_id: int, value: str, chat_id: int
    ) -> ProfileValue:
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile(
                session, bot_user_id, for_update=True
            )
            if profile is None:
                raise FinanceInputError("Jalankan /setup terlebih dahulu.")
            normalized = value.strip().lower()
            if normalized == "on":
                profile.alert_enabled = True
            elif normalized == "off":
                profile.alert_enabled = False
            elif normalized == "here":
                profile.alert_chat_id = chat_id
                profile.alert_enabled = True
            else:
                try:
                    parsed = time.fromisoformat(normalized)
                except ValueError as error:
                    raise FinanceInputError(
                        "Gunakan /alert on, off, here, atau HH:MM."
                    ) from error
                profile.alert_time = parsed.replace(second=0, microsecond=0)
                profile.alert_enabled = True
            profile.last_alert_local_date = None
            profile.alert_claimed_local_date = None
            profile.alert_claimed_at = None
            return self._profile_value(profile)

    async def set_timezone(self, bot_user_id: int, timezone: str) -> ProfileValue:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise FinanceInputError("Timezone IANA tidak dikenali.") from error
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile(
                session, bot_user_id, for_update=True
            )
            if profile is None:
                raise FinanceInputError("Jalankan /setup terlebih dahulu.")
            profile.timezone = timezone
            profile.last_alert_local_date = None
            profile.alert_claimed_local_date = None
            profile.alert_claimed_at = None
            return self._profile_value(profile)

    async def profile(self, bot_user_id: int) -> ProfileValue:
        async with self._database.session() as session:
            profile = await self._repository.get_profile(session, bot_user_id)
            if profile is None:
                raise FinanceInputError("Jalankan /setup terlebih dahulu.")
            return self._profile_value(profile)

    async def claim_due_alerts(self) -> list[AlertClaim]:
        async with self._database.session() as session:
            profile_ids = await self._repository.list_profile_ids(session, self._bot_id)
        claims: list[AlertClaim] = []
        for profile_id in profile_ids:
            await self._ensure_period(profile_id)
            async with self._database.transaction() as session:
                profile = await self._repository.get_profile_by_id(
                    session, profile_id, for_update=True
                )
                if profile is None or not profile.alert_enabled:
                    continue
                local_now = datetime.now(ZoneInfo(profile.timezone))
                claimed_after = utc_now() - timedelta(minutes=5)
                if (
                    local_now.time().replace(tzinfo=None) < profile.alert_time
                    or profile.last_alert_local_date == local_now.date()
                    or (
                        profile.alert_claimed_local_date == local_now.date()
                        and profile.alert_claimed_at is not None
                        and profile.alert_claimed_at > claimed_after
                    )
                ):
                    continue
                period = await self._repository.latest_period(session, profile.id)
                if period is None:
                    continue
                profile.alert_claimed_local_date = local_now.date()
                profile.alert_claimed_at = utc_now()
                claims.append(
                    AlertClaim(
                        self._profile_value(profile),
                        await self._period_value(session, period),
                        local_now.date(),
                    )
                )
        return claims

    async def complete_alert(self, profile_id: int, local_date: date) -> None:
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile_by_id(
                session, profile_id, for_update=True
            )
            if (
                profile is not None
                and profile.alert_claimed_local_date == local_date
            ):
                profile.last_alert_local_date = local_date
                profile.alert_claimed_local_date = None
                profile.alert_claimed_at = None

    async def release_alert(self, profile_id: int, local_date: date) -> None:
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile_by_id(
                session, profile_id, for_update=True
            )
            if (
                profile is not None
                and profile.alert_claimed_local_date == local_date
            ):
                profile.alert_claimed_local_date = None
                profile.alert_claimed_at = None

    async def _profile_id(self, bot_user_id: int) -> int:
        async with self._database.session() as session:
            profile = await self._repository.get_profile(session, bot_user_id)
            if profile is None:
                raise FinanceInputError("Jalankan /setup terlebih dahulu.")
            return profile.id

    async def _ensure_period(self, profile_id: int) -> None:
        async with self._database.transaction() as session:
            profile = await self._repository.get_profile_by_id(
                session, profile_id, for_update=True
            )
            if profile is None:
                return
            today = datetime.now(ZoneInfo(profile.timezone)).date()
            period = await self._repository.latest_period(
                session, profile.id, for_update=True
            )
            if period is None:
                return
            while today > period.end_date:
                if period.effective_budget is None:
                    period.effective_budget = period.base_budget
                    period.applied_carry = 0
                    period.rollover_status = RolloverStatus.AUTO_BASE.value
                    period.rollover_decided_at = utc_now()
                realization = await self._repository.realization(session, period.id)
                balance = period.effective_budget - realization
                start_date = period.end_date + timedelta(days=1)
                end_date = start_date + timedelta(days=profile.recurring_days - 1)
                skipped = end_date < today
                period = await self._repository.create_period(
                    session,
                    profile_id=profile.id,
                    sequence=period.sequence + 1,
                    start_date=start_date,
                    end_date=end_date,
                    base_budget=profile.base_budget,
                    previous_balance=balance,
                    applied_carry=0 if skipped else None,
                    effective_budget=profile.base_budget if skipped else None,
                    rollover_status=(
                        RolloverStatus.AUTO_BASE.value
                        if skipped
                        else RolloverStatus.PENDING.value
                    ),
                    rollover_decided_at=utc_now() if skipped else None,
                )

    async def _period_value(
        self, session: AsyncSession, period: FinanceBudgetPeriodModel
    ) -> PeriodValue:
        realization = await self._repository.realization(session, period.id)
        return PeriodValue(
            id=period.id,
            sequence=period.sequence,
            start_date=period.start_date,
            end_date=period.end_date,
            base_budget=period.base_budget,
            previous_balance=period.previous_balance,
            applied_carry=period.applied_carry,
            effective_budget=period.effective_budget,
            rollover_status=period.rollover_status,
            realization=realization,
        )

    @staticmethod
    def _profile_value(profile: FinanceProfileModel) -> ProfileValue:
        return ProfileValue(
            id=profile.id,
            bot_user_id=profile.bot_user_id,
            base_budget=profile.base_budget,
            recurring_days=profile.recurring_days,
            timezone=profile.timezone,
            alert_enabled=profile.alert_enabled,
            alert_time=profile.alert_time,
            alert_chat_id=profile.alert_chat_id,
        )

    @staticmethod
    def _transaction_value(model: FinanceTransactionModel) -> TransactionValue:
        return TransactionValue(
            id=model.id,
            amount=model.amount,
            purpose=model.purpose,
            spent_on=model.spent_on,
        )

    @staticmethod
    def _validate_transaction_date(
        spent_on: date, today: date, start_date: date, end_date: date
    ) -> None:
        if spent_on > today:
            raise FinanceInputError("Tanggal transaksi tidak boleh di masa depan.")
        if spent_on < start_date or spent_on > end_date:
            raise FinanceInputError("Transaksi harus berada dalam periode aktif.")


class FinanceAlertScheduler:
    def __init__(
        self,
        service: FinanceService,
        deliver: Callable[[AlertClaim], Awaitable[None]],
    ) -> None:
        self._service = service
        self._deliver = deliver
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="finance-alerts")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                claims = await self._service.claim_due_alerts()
                for claim in claims:
                    try:
                        await self._deliver(claim)
                        await self._service.complete_alert(
                            claim.profile.id, claim.local_date
                        )
                    except Exception as error:
                        await self._service.release_alert(
                            claim.profile.id, claim.local_date
                        )
                        await logger.aexception(
                            "finance_alert_delivery_failed",
                            profile_id=claim.profile.id,
                            error_type=type(error).__name__,
                        )
            except Exception as error:
                await logger.aexception(
                    "finance_scheduler_tick_failed",
                    error_type=type(error).__name__,
                )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=30)
            except TimeoutError:
                pass
