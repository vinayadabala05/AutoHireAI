"""Workable public widget API provider.

Public, unauthenticated API:
`GET https://apply.workable.com/api/v1/widget/accounts/{account}`

The widget endpoint's job listing carries a structured `location.remote`
flag and `employment_type` string, but only a shallow description (the
full posting body lives behind a separate per-job endpoint this provider
does not call, to keep one HTTP round trip per `fetch_jobs()` — a future
enhancement could add a detail fetch without changing this class's public
shape).
"""

from datetime import datetime
from typing import Any

from app.job_discovery.models import DiscoveredJob, JobProviderName, JobSearchQuery
from app.job_discovery.parser import extract_skills, guess_experience_level, guess_remote_type
from app.job_discovery.providers.base import BaseJobProvider, register_provider
from app.models.enums import EmploymentType, JobSource, RemoteType

_API_URL_TEMPLATE = "https://apply.workable.com/api/v1/widget/accounts/{account}"

_EMPLOYMENT_TYPE_MAP: dict[str, EmploymentType] = {
    "full-time": EmploymentType.FULL_TIME,
    "part-time": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "internship": EmploymentType.INTERNSHIP,
    "temporary": EmploymentType.TEMPORARY,
    "freelance": EmploymentType.FREELANCE,
}


@register_provider(JobProviderName.WORKABLE)
class WorkableProvider(BaseJobProvider):
    """Fetches postings from a single company's Workable account."""

    def __init__(
        self,
        board_token: str,
        company_name: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(board_token, timeout_seconds)
        self._company_name_override = company_name

    @property
    def provider_name(self) -> JobProviderName:
        return JobProviderName.WORKABLE

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        url = _API_URL_TEMPLATE.format(account=self.board_token)
        payload = await self._get_json(url)
        company_name = self._company_name(payload)
        raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs = [self._parse_job(raw, company_name) for raw in raw_jobs]
        return [job for job in jobs if job is not None][: query.limit]

    def _company_name(self, payload: dict[str, Any]) -> str:
        if self._company_name_override:
            return self._company_name_override
        return str(payload.get("name") or self.board_token.replace("-", " ").title())

    def _parse_job(self, raw: dict[str, Any], company_name: str) -> DiscoveredJob | None:
        title = raw.get("title")
        url = raw.get("url")
        if not title or not url:
            return None

        location = self._location(raw.get("location") or {})
        description = str(raw.get("description") or "")
        employment_type = _EMPLOYMENT_TYPE_MAP.get(
            str(raw.get("employment_type") or "").strip().lower()
        )

        return DiscoveredJob(
            title=title,
            company=company_name,
            location=location,
            remote_type=self._remote_type(raw.get("location") or {}, location, description),
            employment_type=employment_type,
            experience_level=guess_experience_level(title, description),
            description=description,
            skills=extract_skills(title, description),
            source=self.source,
            source_url=url,
            posted_date=_parse_date(raw.get("published_on")),
            metadata={"shortcode": raw.get("shortcode"), "department": raw.get("department")},
        )

    def _location(self, location: dict[str, Any]) -> str | None:
        parts = [location.get("city"), location.get("region"), location.get("country")]
        joined = ", ".join(str(part) for part in parts if part)
        return joined or None

    def _remote_type(
        self, location: dict[str, Any], location_str: str | None, description: str
    ) -> RemoteType | None:
        if location.get("remote") is True:
            return RemoteType.REMOTE
        return guess_remote_type(location_str or "", description)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
