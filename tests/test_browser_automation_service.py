"""Integration tests for `app.browser_automation.service.BrowserAutomationService`."""

from pathlib import Path

import pytest

from app.browser_automation import playwright_manager as playwright_manager_module
from app.browser_automation.exceptions import LoginError
from app.browser_automation.models import (
    FormFieldType,
    LoginCredentials,
    PortalType,
    SubmissionStatus,
)
from app.browser_automation.playwright_manager import PlaywrightManager
from app.browser_automation.portal import GreenhouseAdapter
from app.browser_automation.service import BrowserAutomationService
from app.browser_automation.session import SessionStore
from tests.browser_automation_fixtures import FakePage, fake_async_playwright_factory
from tests.resume_fixtures import sample_career_profile


@pytest.fixture(autouse=True)
def _patch_async_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        playwright_manager_module, "async_playwright", fake_async_playwright_factory
    )


async def _package():
    from app.application_planning.package_builder import ApplicationPackageBuilder
    from app.cover_letter.service import CoverLetterGenerationService
    from app.intelligence.resume_planner import ResumePlanner
    from app.resume.service import ResumeGenerationService
    from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
    from tests.job_discovery_fixtures import sample_job
    from tests.resume_fixtures import make_llm_service

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_llm_service([])),
        enhance_with_llm=False,
    )
    return await builder.build(sample_job(), sample_career_profile(), blueprint, "job-1")


async def test_login_success_saves_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.browser_automation_fixtures import FakeBrowserContext

    original_new_page = FakeBrowserContext.new_page

    async def _new_page_with_login_indicator(self: FakeBrowserContext) -> FakePage:
        page = await original_new_page(self)
        page.selector_counts["a:has-text('Sign out')"] = 1
        return page

    monkeypatch.setattr(FakeBrowserContext, "new_page", _new_page_with_login_indicator)

    service = BrowserAutomationService(
        manager=PlaywrightManager(), session_store=SessionStore(directory=tmp_path)
    )
    session = await service.login(
        PortalType.GREENHOUSE,
        "acct1",
        LoginCredentials(username="jordan@example.com", password="hunter2"),
        "https://example.com/login",
    )
    assert session.account_key == "acct1"
    assert Path(session.storage_state_path).exists()


async def test_login_raises_when_not_logged_in_after_submit(tmp_path: Path) -> None:
    service = BrowserAutomationService(
        manager=PlaywrightManager(), session_store=SessionStore(directory=tmp_path)
    )
    with pytest.raises(LoginError):
        await service.login(
            PortalType.GREENHOUSE,
            "acct1",
            LoginCredentials(username="jordan@example.com", password="hunter2"),
            "https://example.com/login",
        )


async def test_validate_session_false_when_never_logged_in(tmp_path: Path) -> None:
    service = BrowserAutomationService(session_store=SessionStore(directory=tmp_path))
    assert await service.validate_session(PortalType.GREENHOUSE, "acct1", FakePage()) is False


async def test_validate_session_true_when_adapter_confirms_login(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    service = BrowserAutomationService(session_store=store)

    from tests.browser_automation_fixtures import FakeBrowserContext

    await store.save(PortalType.GREENHOUSE, "acct1", FakeBrowserContext())
    page = FakePage()
    page.selector_counts["a:has-text('Sign out')"] = 1

    assert await service.validate_session(PortalType.GREENHOUSE, "acct1", page) is True


async def test_fill_application_delegates_to_form_filler() -> None:
    service = BrowserAutomationService()
    page = FakePage()
    adapter = GreenhouseAdapter()
    for selector in adapter.field_selectors.values():
        page.selector_counts[selector] = 1

    result = await service.fill_application(PortalType.GREENHOUSE, page, sample_career_profile())
    assert FormFieldType.FULL_NAME in result.filled_fields


async def test_upload_documents_uploads_resume_and_cover_letter() -> None:
    service = BrowserAutomationService()
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    package = await _package()

    results = await service.upload_documents(PortalType.GREENHOUSE, page, package)
    assert len(results) == 2
    assert all(r.uploaded for r in results)


async def test_submit_application_runs_full_flow_and_enriches_metadata() -> None:
    from datetime import UTC, datetime

    from app.application_planning.models import (
        ApplicationDecision,
        ApplicationPlan,
        ApplicationPriority,
    )
    from tests.job_discovery_fixtures import sample_job

    service = BrowserAutomationService()
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    package = await _package()
    job = sample_job()
    plan = ApplicationPlan(
        job_id="job-1",
        company="Acme Corp",
        title="Backend Engineer",
        match_score=85.0,
        decision=ApplicationDecision.APPLY,
        priority=ApplicationPriority.HIGH,
        timestamp=datetime.now(UTC),
    )

    result = await service.submit_application(
        PortalType.GREENHOUSE, page, package, sample_career_profile(), plan=plan, job=job
    )

    assert result.status is SubmissionStatus.SUBMITTED
    assert result.metadata["priority"] == "high"
    assert result.metadata["match_score"] == 85.0
    assert result.metadata["job_location"] == job.location
