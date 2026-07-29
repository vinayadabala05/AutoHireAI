from pydantic import BaseModel, EmailStr

from app.schemas.common import SoftDeletableResponse


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    timezone: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class UserResponse(SoftDeletableResponse):
    email: EmailStr
    full_name: str
    phone: str | None
    location: str | None
    headline: str | None
    summary: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    timezone: str | None
    is_active: bool
