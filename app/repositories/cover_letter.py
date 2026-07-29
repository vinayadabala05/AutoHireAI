import uuid

from sqlalchemy import select

from app.models.cover_letter import CoverLetter
from app.repositories.base import BaseRepository


class CoverLetterRepository(BaseRepository[CoverLetter]):
    model = CoverLetter

    async def list_by_user(self, user_id: uuid.UUID) -> list[CoverLetter]:
        stmt = self._apply_not_deleted(
            select(CoverLetter).where(CoverLetter.user_id == user_id), include_deleted=False
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_application(self, application_id: uuid.UUID) -> CoverLetter | None:
        stmt = self._apply_not_deleted(
            select(CoverLetter).where(CoverLetter.application_id == application_id),
            include_deleted=False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
