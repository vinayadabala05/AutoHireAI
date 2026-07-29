from sqlalchemy import select

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    async def get_by_name(self, name: str, *, include_deleted: bool = False) -> Company | None:
        stmt = self._apply_not_deleted(select(Company).where(Company.name == name), include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
