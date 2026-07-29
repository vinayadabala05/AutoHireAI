"""Greenhouse Job Board API provider.

Public, unauthenticated API:
`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`

Greenhouse gives no structured salary, remote/hybrid flag, or employment
type — only a title, a location string, and an HTML job description — so
this provider leans on `parser.py`'s text-heuristics for everything beyond
the literal fields the API returns.
"""

from datetime import datetime
from typing import Any

from app.job_discovery.models import DiscoveredJob, JobProviderName, JobSearchQuery
from app.job_discovery.parser import (
    extract_salary_from_text,
    extract_skills,
    guess_experience_level,
    guess_remote_type,
    normalize_location,
    strip_html,
)
from app.job_discovery.providers.base import BaseJobProvider, register_provider
from app.models.enums import JobSource

_API_URL_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"


@register_provider(JobProviderName.GREENHOUSE)
class GreenhouseProvider(BaseJobProvider):
    """Fetches postings from a single company's Greenhouse job board."""

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
        return JobProviderName.GREENHOUSE

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        url = _API_URL_TEMPLATE.format(board_token=self.board_token)
        payload = await self._get_json(url, params={"content": "true"})
        raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        jobs = [self._parse_job(raw) for raw in raw_jobs]
        return [job for job in jobs if job is not None][: query.limit]

    def _parse_job(self, raw: dict[str, Any]) -> DiscoveredJob | None:
        title = raw.get("title")
        url = raw.get("absolute_url")
        if not title or not url:
            return None

        description = strip_html(raw.get("content"))
        location_name = (raw.get("location") or {}).get("name")
        location = normalize_location(location_name)
        salary_min, salary_max, currency = extract_salary_from_text(description)

        return DiscoveredJob(
            title=title,
            company=self.company_name,
            location=location,
            remote_type=guess_remote_type(location or "", description),
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            experience_level=guess_experience_level(title, description),
            description=description,
            skills=extract_skills(title, description),
            source=self.source,
            source_url=url,
            posted_date=_parse_datetime(raw.get("updated_at")),
            metadata={"greenhouse_id": raw.get("id")},
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
