"""Unit tests for `app.job_monitoring.dispatcher.JobDispatcher`."""

import pytest

from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.service import ApplicationPlanningService
from app.browser_automation.models import FormFieldType, PortalType
from app.browser_automation.portal import GreenhouseAdapter
from app.browser_automation.service import BrowserAutomationService
from app.cover_letter.service import CoverLetterGenerationService
from app.intelligence.resume_planner import ResumePlanner
from app.job_monitoring.dispatcher import JobDispatcher
from app.job_monitoring.exceptions import DispatchError
from app.job_monitoring.models import ProcessingOutcome
from app.resume.service import ResumeGenerationService
from tests.browser_automation_fixtures import FakePage
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.job_discovery_fixtures import sample_job
from tests.resume_fixtures import make_llm_service, sample_career_profile


class _FakeBrowserSession:
    def __init__(self, page: FakePage) -> None:
        self._page = page

    async def new_page(self) -> FakePage:
        return self._page


def _planning_service() -> ApplicationPlanningService:
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    return ApplicationPlanningService(package_builder=builder)


def _blueprint():
    return ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())


def _ready_page() -> FakePage:
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    return page


async def test_dispatch_returns_submitted_outcome() -> None:
    page = _ready_page()
    dispatcher = JobDispatcher(
        _planning_service(),
        BrowserAutomationService(),
        _FakeBrowserSession(page),
        PortalType.GREENHOUSE,
    )
    outcome = await dispatcher.dispatch(sample_job(), sample_career_profile(), _blueprint())
    assert outcome.outcome is ProcessingOutcome.SUBMITTED
    assert outcome.application_url


async def test_dispatch_closes_the_page_on_success() -> None:
    page = _ready_page()
    dispatcher = JobDispatcher(
        _planning_service(),
        BrowserAutomationService(),
        _FakeBrowserSession(page),
        PortalType.GREENHOUSE,
    )
    await dispatcher.dispatch(sample_job(), sample_career_profile(), _blueprint())
    assert page.closed is True


async def test_dispatch_closes_the_page_on_failure() -> None:
    page = FakePage()  # missing all selectors -> submission fails
    dispatcher = JobDispatcher(
        _planning_service(),
        BrowserAutomationService(),
        _FakeBrowserSession(page),
        PortalType.GREENHOUSE,
    )
    outcome = await dispatcher.dispatch(sample_job(), sample_career_profile(), _blueprint())
    assert outcome.outcome is ProcessingOutcome.FAILED
    assert page.closed is True


async def test_dispatch_raises_dispatch_error_when_planning_fails() -> None:
    from tests.resume_fixtures import profile_with_no_skills

    page = _ready_page()
    dispatcher = JobDispatcher(
        _planning_service(),
        BrowserAutomationService(),
        _FakeBrowserSession(page),
        PortalType.GREENHOUSE,
    )
    with pytest.raises(DispatchError):
        await dispatcher.dispatch(sample_job(), profile_with_no_skills(), _blueprint())
    assert page.closed is True


async def test_dispatch_uses_provided_job_id() -> None:
    page = _ready_page()
    dispatcher = JobDispatcher(
        _planning_service(),
        BrowserAutomationService(),
        _FakeBrowserSession(page),
        PortalType.GREENHOUSE,
    )
    outcome = await dispatcher.dispatch(
        sample_job(), sample_career_profile(), _blueprint(), job_id="custom-id"
    )
    assert outcome.outcome is ProcessingOutcome.SUBMITTED
