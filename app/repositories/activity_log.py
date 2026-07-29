import uuid

from sqlalchemy import select

from app.models.activity_log import ActivityLog
from app.repositories.base import BaseRepository


class ActivityLogRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    async def list_by_user(self, user_id: uuid.UUID, *, limit: int = 100) -> list[ActivityLog]:
        stmt = (
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.occurred_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
