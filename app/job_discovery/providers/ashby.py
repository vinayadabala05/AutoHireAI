"""Ashby Job Board API provider.

Public, unauthenticated API:
`GET https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true`

Ashby is the most structured of the four boards: it gives a boolean
`isRemote`, a normalized `employmentType`, and (with
`includeCompensation=true`) a real compensation range — so this provider
needs `parser.py`'s heuristics only as a fallback when a field is absent.
"""

from datetime import datetime
from typing import Any

from app.job_discovery.models import DiscoveredJob, JobProviderName, JobSearchQuery
from app.job_discovery.parser import (
    extract_skills,
    guess_experience_level,
    guess_remote_type,
    normalize_location,
    strip_html,
)
from app.job_discovery.providers.base import BaseJobProvider, register_provider
from app.models.enums import EmploymentType, JobSource, RemoteType

_API_URL_TEMPLATE = "https://api.ashbyhq.com/posting-api/job-board/{board_token}"

_EMPLOYMENT_TYPE_MAP: dict[str, EmploymentType] = {
    "fulltime": EmploymentType.FULL_TIME,
    "parttime": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "intern": EmploymentType.INTERNSHIP,
    "internship": EmploymentType.INTERNSHIP,
    "temporary": EmploymentType.TEMPORARY,
    "freelance": EmploymentType.FREELANCE,
}


@register_provider(JobProviderName.ASHBY)
class AshbyProvider(BaseJobProvider):
    """Fetches postings from a single company's Ashby job board."""

    def __init__(
        self,
        board_token: str,
        company_name: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(board_token, timeout_seconds)
        self.company_name = company_name or board_token.replace("-", " ").title()

    @property
    def provider_name(self) -> JobProviderName:
        return JobProviderName.ASHBY

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        url = _API_URL_TEMPLATE.format(board_token=self.board_token)
        payload = await self._get_json(url, params={"includeCompensation": "true"})
        raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs = [self._parse_job(raw) for raw in raw_jobs]
        return [job for job in jobs if job is not None][: query.limit]

    def _parse_job(self, raw: dict[str, Any]) -> DiscoveredJob | None:
        title = raw.get("title")
        url = raw.get("jobUrl") or raw.get("applyUrl")
        if not title or not url:
            return None

        description = strip_html(raw.get("descriptionHtml"))
        location = normalize_location(raw.get("location"))
        salary_min, salary_max, currency = self._compensation(raw)
        employment_type = _EMPLOYMENT_TYPE_MAP.get(
            str(raw.get("employmentType") or "").strip().lower()
        )

        return DiscoveredJob(
            title=title,
            company=self.company_name,
            location=location,
            remote_type=self._remote_type(raw, location, description),
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            employment_type=employment_type,
            experience_level=guess_experience_level(title, description),
            description=description,
            skills=extract_skills(title, description),
            source=self.source,
            source_url=url,
            posted_date=_parse_datetime(raw.get("publishedAt")),
            metadata={"ashby_id": raw.get("id"), "department": raw.get("department")},
        )

    def _remote_type(
        self, raw: dict[str, Any], location: str | None, description: str
    ) -> RemoteType | None:
        if raw.get("isRemote") is True:
            return RemoteType.REMOTE
        return guess_remote_type(location or "", description)

    def _compensation(self, raw: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
        compensation = raw.get("compensation") or {}
        components = compensation.get("summaryComponents") or []
        for component in components:
            min_value = component.get("minValue")
            max_value = component.get("maxValue")
            if min_value is not None or max_value is not None:
                return (
                    float(min_value) if min_value is not None else None,
                    float(max_value) if max_value is not None else None,
                    component.get("currencyCode"),
                )
        return None, None, None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
