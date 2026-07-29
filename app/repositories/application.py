import uuid

from sqlalchemy import select

from app.models.application import Application, ApplicationEvent
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    model = Application

    async def get_by_user_and_job(
        self, user_id: uuid.UUID, job_id: uuid.UUID, *, include_deleted: bool = False
    ) -> Application | None:
        stmt = self._apply_not_deleted(
            select(Application).where(Application.user_id == user_id, Application.job_id == job_id),
            include_deleted,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Application]:
        stmt = self._apply_not_deleted(
            select(Application).where(Application.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ApplicationEventRepository(BaseRepository[ApplicationEvent]):
    model = ApplicationEvent

    async def list_by_application(self, application_id: uuid.UUID) -> list[ApplicationEvent]:
        stmt = (
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id == application_id)
            .order_by(ApplicationEvent.occurred_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
