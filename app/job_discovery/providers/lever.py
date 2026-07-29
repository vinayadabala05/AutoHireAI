"""Lever Postings API provider.

Public, unauthenticated API:
`GET https://api.lever.co/v0/postings/{board_token}?mode=json`

Unlike Greenhouse, Lever gives a structured `categories.commitment`
(employment type) and, on many boards, a `workplaceType` field
(remote/hybrid/onsite) — used directly when present, falling back to
`parser.py`'s text heuristics otherwise.
"""

import re
from datetime import UTC, datetime
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
from app.models.enums import EmploymentType, JobSource, RemoteType

_API_URL_TEMPLATE = "https://api.lever.co/v0/postings/{board_token}"
_LIST_ITEM_PATTERN = re.compile(r"<li[^>]*>|</li>", re.IGNORECASE)

_COMMITMENT_TO_EMPLOYMENT_TYPE: dict[str, EmploymentType] = {
    "full-time": EmploymentType.FULL_TIME,
    "part-time": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "internship": EmploymentType.INTERNSHIP,
    "temporary": EmploymentType.TEMPORARY,
    "freelance": EmploymentType.FREELANCE,
}

_WORKPLACE_TYPE_TO_REMOTE_TYPE: dict[str, RemoteType] = {
    "remote": RemoteType.REMOTE,
    "hybrid": RemoteType.HYBRID,
    "onsite": RemoteType.ONSITE,
}


@register_provider(JobProviderName.LEVER)
class LeverProvider(BaseJobProvider):
    """Fetches postings from a single company's Lever job board."""

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
        return JobProviderName.LEVER

    @property
    def source(self) -> JobSource:
        return JobSource.COMPANY_SITE

    async def fetch_jobs(self, query: JobSearchQuery) -> list[DiscoveredJob]:
        url = _API_URL_TEMPLATE.format(board_token=self.board_token)
        payload = await self._get_json(url, params={"mode": "json"})
        raw_jobs = payload if isinstance(payload, list) else []
        jobs = [self._parse_job(raw) for raw in raw_jobs]
        return [job for job in jobs if job is not None][: query.limit]

    def _parse_job(self, raw: dict[str, Any]) -> DiscoveredJob | None:
        title = raw.get("text")
        url = raw.get("hostedUrl")
        if not title or not url:
            return None

        categories = raw.get("categories") or {}
        location = normalize_location(categories.get("location"))
        description = strip_html(raw.get("descriptionPlain") or raw.get("description"))
        requirements = self._parse_lists(raw.get("lists") or [])
        commitment = str(categories.get("commitment") or "").strip().lower()
        salary_min, salary_max, currency = extract_salary_from_text(description)

        return DiscoveredJob(
            title=title,
            company=self.company_name,
            location=location,
            remote_type=self._remote_type(raw, location, description),
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            employment_type=_COMMITMENT_TO_EMPLOYMENT_TYPE.get(commitment),
            experience_level=guess_experience_level(title, description),
            description=description,
            requirements=requirements,
            skills=extract_skills(title, description, " ".join(requirements)),
            source=self.source,
            source_url=url,
            posted_date=_parse_epoch_ms(raw.get("createdAt")),
            metadata={"lever_id": raw.get("id"), "team": categories.get("team")},
        )

    def _remote_type(
        self, raw: dict[str, Any], location: str | None, description: str
    ) -> RemoteType | None:
        workplace_type = str(raw.get("workplaceType") or "").strip().lower()
        if workplace_type in _WORKPLACE_TYPE_TO_REMOTE_TYPE:
            return _WORKPLACE_TYPE_TO_REMOTE_TYPE[workplace_type]
        return guess_remote_type(location or "", description)

    def _parse_lists(self, lists: list[dict[str, Any]]) -> list[str]:
        """Split each `lists[].content` HTML fragment on `<li>` boundaries.

        Lever's real API returns each requirements/benefits section as an
        HTML `<ul><li>...</li></ul>` fragment — splitting on list-item
        boundaries first (before stripping tags) is what turns that into
        one requirement string per bullet, instead of one long line.
        """
        requirements: list[str] = []
        for entry in lists:
            content = entry.get("content") or ""
            for fragment in _LIST_ITEM_PATTERN.split(content):
                text = strip_html(fragment)
                if text:
                    requirements.append(text)
        return requirements


def _parse_epoch_ms(value: object) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None
