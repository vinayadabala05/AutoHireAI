"""Generic async CRUD repository.

Concrete repositories (`UserRepository`, `JobRepository`, ...) subclass
`BaseRepository[Model]` and add only query methods specific to that model —
get/list/create/update/delete are implemented once here instead of being
copy-pasted per entity.

Soft delete is applied automatically wherever the model has a `deleted_at`
column (i.e. inherits `SoftDeleteMixin`); models that don't (`ApplicationEvent`,
`ActivityLog` — append-only audit trails) fall back to a real `DELETE`.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    def _supports_soft_delete(self) -> bool:
        return hasattr(self.model, "deleted_at")

    def _apply_not_deleted(self, stmt: Select[Any], include_deleted: bool) -> Select[Any]:
        if not include_deleted and self._supports_soft_delete:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    async def get(self, id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        stmt = self._apply_not_deleted(stmt, include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, *, limit: int = 50, offset: int = 0, include_deleted: bool = False
    ) -> list[ModelT]:
        stmt = self._apply_not_deleted(select(self.model), include_deleted)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **fields: Any) -> ModelT:
        instance = self.model(**fields)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, **fields: Any) -> ModelT:
        for key, value in fields.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Soft-delete if the model supports it, otherwise a real DELETE."""
        if self._supports_soft_delete:
            instance.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
            await self.session.flush()
        else:
            await self.session.delete(instance)
            await self.session.flush()
