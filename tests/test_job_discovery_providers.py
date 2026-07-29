"""Unit tests for `app.job_discovery.providers` — registry, base contract,
and each concrete provider's payload parsing.

Every HTTP call is mocked at the `_get_json` boundary (never real network),
mirroring the pattern `tests/test_llm_providers.py` uses for LLM providers:
monkeypatch the one protected method that actually calls `httpx`.
"""

import httpx
import pytest

from app.job_discovery.exceptions import ProviderFetchError, ProviderNotFoundError
from app.job_discovery.models import JobProviderName, JobSearchQuery
from app.job_discovery.providers.ashby import AshbyProvider
from app.job_discovery.providers.base import available_providers, get_provider_class
from app.job_discovery.providers.greenhouse import GreenhouseProvider
from app.job_discovery.providers.lever import LeverProvider
from app.job_discovery.providers.workable import WorkableProvider
from app.models.enums import EmploymentType, JobSource, RemoteType


def test_available_providers_includes_all_four_built_ins() -> None:
    assert set(available_providers()) == {
        JobProviderName.GREENHOUSE,
        JobProviderName.LEVER,
        JobProviderName.ASHBY,
        JobProviderName.WORKABLE,
    }


def test_get_provider_class_returns_registered_class() -> None:
    assert get_provider_class(JobProviderName.GREENHOUSE) is GreenhouseProvider
    assert get_provider_class(JobProviderName.LEVER) is LeverProvider
    assert get_provider_class(JobProviderName.ASHBY) is AshbyProvider
    assert get_provider_class(JobProviderName.WORKABLE) is WorkableProvider


def test_get_provider_class_raises_for_unregistered_name() -> None:
    with pytest.raises(ProviderNotFoundError):
        get_provider_class("not-a-real-provider")  # type: ignore[arg-type]


async def test_health_check_returns_true_when_fetch_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GreenhouseProvider(board_token="acme")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return {"jobs": []}

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    assert await provider.health_check() is True


async def test_health_check_returns_false_on_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")

    async def _raise(self: object, url: str, params: dict | None = None) -> dict:
        raise ProviderFetchError("boom")

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _raise)
    assert await provider.health_check() is False


async def test_get_json_returns_parsed_json_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"jobs": []}

    class _SucceedingClient:
        async def __aenter__(self) -> "_SucceedingClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
            return _FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _SucceedingClient())
    result = await provider._get_json("https://example.com")
    assert result == {"jobs": []}


async def test_get_json_wraps_httpx_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")

    class _FailingClient:
        async def __aenter__(self) -> "_FailingClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, params: dict | None = None) -> None:
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FailingClient())
    with pytest.raises(ProviderFetchError):
        await provider._get_json("https://example.com")


# ---------------------------------------------------------------------------
# Greenhouse
# ---------------------------------------------------------------------------

_GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 1,
            "title": "Senior Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            "location": {"name": "Remote - US"},
            "content": "<p>Build APIs with Python and FastAPI. Salary: $140,000 - $170,000.</p>",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        {"id": 2, "title": "Missing URL"},  # malformed: no absolute_url, should be skipped
    ]
}


async def test_greenhouse_parses_jobs_and_skips_malformed_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GreenhouseProvider(board_token="acme", company_name="Acme Corp")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        assert "acme" in url
        return _GREENHOUSE_PAYLOAD

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Backend Engineer"
    assert job.company == "Acme Corp"
    assert job.source is JobSource.COMPANY_SITE
    assert job.remote_type is RemoteType.REMOTE
    assert job.salary_min == 140000.0
    assert job.salary_max == 170000.0
    assert "Python" in job.skills
    assert job.metadata["greenhouse_id"] == 1


async def test_greenhouse_defaults_company_name_from_board_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GreenhouseProvider(board_token="acme-corp")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return {"jobs": []}

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    assert provider.company_name == "Acme Corp"
    assert provider.provider_name is JobProviderName.GREENHOUSE


async def test_greenhouse_respects_query_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")
    payload = {
        "jobs": [
            {**_GREENHOUSE_PAYLOAD["jobs"][0], "id": 10, "absolute_url": "https://x/10"},
            {**_GREENHOUSE_PAYLOAD["jobs"][0], "id": 11, "absolute_url": "https://x/11"},
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery(limit=1))
    assert len(jobs) == 1


async def test_greenhouse_handles_unparseable_updated_at(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")
    payload = {
        "jobs": [
            {
                "id": 3,
                "title": "Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/3",
                "location": {},
                "content": "",
                "updated_at": "not-a-date",
            }
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None


async def test_greenhouse_handles_missing_updated_at(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GreenhouseProvider(board_token="acme")
    payload = {
        "jobs": [
            {
                "id": 4,
                "title": "Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/4",
            }
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(GreenhouseProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None


# ---------------------------------------------------------------------------
# Lever
# ---------------------------------------------------------------------------

_LEVER_PAYLOAD = [
    {
        "id": "abc123",
        "text": "Staff Backend Engineer",
        "categories": {"location": "New York, NY", "commitment": "Full-time", "team": "Platform"},
        "descriptionPlain": "Own our core services.",
        "lists": [
            {
                "text": "Requirements",
                "content": "<ul><li>5+ years Python</li><li>Docker experience</li></ul>",
            }
        ],
        "hostedUrl": "https://jobs.lever.co/acme/abc123",
        "workplaceType": "hybrid",
        "createdAt": 1700000000000,
    },
    {"id": "no-url", "text": "Broken Posting"},
]


async def test_lever_parses_jobs_and_skips_malformed_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = LeverProvider(board_token="acme", company_name="Acme Corp")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> list:
        return _LEVER_PAYLOAD

    monkeypatch.setattr(LeverProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Staff Backend Engineer"
    assert job.location == "New York, NY"
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.remote_type is RemoteType.HYBRID
    assert "Docker experience" in job.requirements
    assert job.posted_date is not None
    assert job.metadata["team"] == "Platform"


async def test_lever_falls_back_to_text_heuristic_when_no_workplace_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = LeverProvider(board_token="acme")
    payload = [
        {
            "id": "x",
            "text": "Engineer",
            "categories": {"location": "Remote", "commitment": "Contract"},
            "descriptionPlain": "Fully remote role.",
            "hostedUrl": "https://jobs.lever.co/acme/x",
        }
    ]

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> list:
        return payload

    monkeypatch.setattr(LeverProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].remote_type is RemoteType.REMOTE
    assert jobs[0].employment_type is EmploymentType.CONTRACT


async def test_lever_handles_non_list_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = LeverProvider(board_token="acme")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return {"unexpected": "shape"}

    monkeypatch.setattr(LeverProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs == []


async def test_lever_handles_invalid_created_at(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = LeverProvider(board_token="acme")
    payload = [
        {
            "id": "x",
            "text": "Engineer",
            "categories": {},
            "hostedUrl": "https://jobs.lever.co/acme/x",
            "createdAt": "not-a-number",
        }
    ]

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> list:
        return payload

    monkeypatch.setattr(LeverProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None


async def test_lever_handles_out_of_range_created_at(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = LeverProvider(board_token="acme")
    assert provider.provider_name is JobProviderName.LEVER
    payload = [
        {
            "id": "x",
            "text": "Engineer",
            "categories": {},
            "hostedUrl": "https://jobs.lever.co/acme/x",
            "createdAt": float("inf"),
        }
    ]

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> list:
        return payload

    monkeypatch.setattr(LeverProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None


# ---------------------------------------------------------------------------
# Ashby
# ---------------------------------------------------------------------------

_ASHBY_PAYLOAD = {
    "jobs": [
        {
            "id": "job-1",
            "title": "Senior AI Engineer",
            "location": "San Francisco, CA",
            "isRemote": True,
            "descriptionHtml": "<p>Work on LLM systems with Python.</p>",
            "publishedAt": "2026-01-01T00:00:00.000Z",
            "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
            "employmentType": "FullTime",
            "department": "Engineering",
            "compensation": {
                "summaryComponents": [
                    {"minValue": 180000, "maxValue": 220000, "currencyCode": "USD"}
                ]
            },
        },
        {"id": "job-2", "title": "No URL Job"},
    ]
}


async def test_ashby_parses_jobs_and_skips_malformed_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AshbyProvider(board_token="acme", company_name="Acme Corp")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return _ASHBY_PAYLOAD

    monkeypatch.setattr(AshbyProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior AI Engineer"
    assert job.remote_type is RemoteType.REMOTE
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.salary_min == 180000.0
    assert job.salary_max == 220000.0
    assert job.currency == "USD"
    assert job.metadata["department"] == "Engineering"


async def test_ashby_falls_back_to_text_heuristics_when_fields_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AshbyProvider(board_token="acme")
    payload = {
        "jobs": [
            {
                "id": "job-3",
                "title": "Engineer",
                "location": "Hybrid - Austin, TX",
                "descriptionHtml": "<p>Some hybrid role.</p>",
                "jobUrl": "https://jobs.ashbyhq.com/acme/job-3",
            }
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(AshbyProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].remote_type is RemoteType.HYBRID
    assert jobs[0].employment_type is None
    assert jobs[0].salary_min is None


async def test_ashby_uses_apply_url_when_job_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = AshbyProvider(board_token="acme")
    payload = {
        "jobs": [
            {
                "id": "job-4",
                "title": "Engineer",
                "applyUrl": "https://jobs.ashbyhq.com/acme/apply/job-4",
            }
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(AshbyProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].source_url == "https://jobs.ashbyhq.com/acme/apply/job-4"


async def test_ashby_handles_unparseable_published_at(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = AshbyProvider(board_token="acme")
    assert provider.provider_name is JobProviderName.ASHBY
    payload = {
        "jobs": [
            {"id": "job-5", "title": "Engineer", "jobUrl": "https://x/5", "publishedAt": "bad-date"}
        ]
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(AshbyProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None


# ---------------------------------------------------------------------------
# Workable
# ---------------------------------------------------------------------------

_WORKABLE_PAYLOAD = {
    "name": "Acme Corp",
    "jobs": [
        {
            "title": "Backend Developer",
            "shortcode": "ABC123",
            "location": {
                "city": "Austin",
                "region": "TX",
                "country": "United States",
                "remote": True,
            },
            "url": "https://apply.workable.com/acme/j/ABC123/",
            "department": "Engineering",
            "employment_type": "Full-time",
            "published_on": "2026-01-01",
            "description": "",
        },
        {"title": "No URL Job"},
    ],
}


async def test_workable_parses_jobs_and_skips_malformed_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WorkableProvider(board_token="acme")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return _WORKABLE_PAYLOAD

    monkeypatch.setattr(WorkableProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Backend Developer"
    assert job.company == "Acme Corp"
    assert job.location == "Austin, TX, United States"
    assert job.remote_type is RemoteType.REMOTE
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.posted_date is not None
    assert job.metadata["shortcode"] == "ABC123"


async def test_workable_company_name_override_takes_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = WorkableProvider(board_token="acme", company_name="Custom Name")

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return _WORKABLE_PAYLOAD

    monkeypatch.setattr(WorkableProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].company == "Custom Name"


async def test_workable_handles_missing_published_on(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = WorkableProvider(board_token="acme")
    payload = {
        "name": "Acme",
        "jobs": [
            {
                "title": "Engineer",
                "url": "https://apply.workable.com/acme/j/X/",
                "location": {},
            }
        ],
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(WorkableProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None
    assert jobs[0].location is None


async def test_workable_handles_unparseable_published_on(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = WorkableProvider(board_token="acme")
    assert provider.provider_name is JobProviderName.WORKABLE
    payload = {
        "name": "Acme",
        "jobs": [{"title": "Engineer", "url": "https://x/1", "published_on": "not-a-date"}],
    }

    async def _fake_get_json(self: object, url: str, params: dict | None = None) -> dict:
        return payload

    monkeypatch.setattr(WorkableProvider, "_get_json", _fake_get_json)
    jobs = await provider.fetch_jobs(JobSearchQuery())
    assert jobs[0].posted_date is None
