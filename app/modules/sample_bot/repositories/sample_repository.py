from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sample_bot.models import SampleUserProfileModel


class SampleRepository:
    async def touch_profile(
        self, session: AsyncSession, bot_user_id: int
    ) -> SampleUserProfileModel:
        statement = (
            insert(SampleUserProfileModel)
            .values(bot_user_id=bot_user_id)
            .on_conflict_do_update(
                index_elements=[SampleUserProfileModel.bot_user_id],
                set_={"last_command_at": func.now()},
            )
            .returning(SampleUserProfileModel)
        )
        return (await session.scalars(statement)).one()

