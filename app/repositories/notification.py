import uuid

from sqlalchemy import select

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_unread(self, user_id: uuid.UUID) -> list[Notification]:
        stmt = self._apply_not_deleted(
            select(Notification).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            ),
            include_deleted=False,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
