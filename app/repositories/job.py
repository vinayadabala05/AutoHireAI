import uuid

from sqlalchemy import select

from app.models.enums import JobSource
from app.models.job import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    async def get_by_source_external_id(
        self, source: JobSource, external_id: str, *, include_deleted: bool = False
    ) -> Job | None:
        stmt = self._apply_not_deleted(
            select(Job).where(Job.source == source, Job.external_id == external_id),
            include_deleted,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_company(self, company_id: uuid.UUID) -> list[Job]:
        stmt = self._apply_not_deleted(
            select(Job).where(Job.company_id == company_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
