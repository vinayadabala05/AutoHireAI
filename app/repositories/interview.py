import uuid

from sqlalchemy import select

from app.models.interview import BehaviorAnswer, Interview, TechnicalAnswer
from app.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[Interview]):
    model = Interview

    async def list_by_application(self, application_id: uuid.UUID) -> list[Interview]:
        stmt = self._apply_not_deleted(
            select(Interview).where(Interview.application_id == application_id),
            include_deleted=False,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class BehaviorAnswerRepository(BaseRepository[BehaviorAnswer]):
    model = BehaviorAnswer

    async def list_by_user(self, user_id: uuid.UUID) -> list[BehaviorAnswer]:
        stmt = self._apply_not_deleted(
            select(BehaviorAnswer).where(BehaviorAnswer.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TechnicalAnswerRepository(BaseRepository[TechnicalAnswer]):
    model = TechnicalAnswer

    async def list_by_user(self, user_id: uuid.UUID) -> list[TechnicalAnswer]:
        stmt = self._apply_not_deleted(
            select(TechnicalAnswer).where(TechnicalAnswer.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
