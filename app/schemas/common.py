"""Shared Pydantic v2 base classes for request/response DTOs.

`Create`/`Update` schemas are plain `BaseModel`s (nothing to read from an
ORM instance yet); `Response` schemas set `from_attributes=True` so they
can be built directly from a SQLAlchemy model with `Model.model_validate(orm_obj)`.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedResponse(ORMBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SoftDeletableResponse(TimestampedResponse):
    deleted_at: datetime | None = None
