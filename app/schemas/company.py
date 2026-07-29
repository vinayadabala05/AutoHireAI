from pydantic import BaseModel

from app.schemas.common import SoftDeletableResponse


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    location: str | None = None
    description: str | None = None
    logo_url: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    location: str | None = None
    description: str | None = None
    logo_url: str | None = None


class CompanyResponse(SoftDeletableResponse):
    name: str
    website: str | None
    industry: str | None
    size: str | None
    location: str | None
    description: str | None
    logo_url: str | None
