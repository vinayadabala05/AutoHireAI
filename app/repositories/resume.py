import uuid

from sqlalchemy import func, select

from app.models.resume import Resume, ResumeVersion
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    model = Resume

    async def list_by_user(self, user_id: uuid.UUID) -> list[Resume]:
        stmt = self._apply_not_deleted(
            select(Resume).where(Resume.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ResumeVersionRepository(BaseRepository[ResumeVersion]):
    model = ResumeVersion

    async def list_by_resume(self, resume_id: uuid.UUID) -> list[ResumeVersion]:
        stmt = self._apply_not_deleted(
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc()),
            include_deleted=False,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def next_version_number(self, resume_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(ResumeVersion.version_number), 0)).where(
            ResumeVersion.resume_id == resume_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() + 1
