"""Shared test fixtures for Sprint 12 Application State & Recovery Engine tests.

Builds a real `JobMonitoringService` (Sprint 11) wired to a real
`ApplicationPlanningService` (Sprint 9) and `BrowserAutomationService`
(Sprint 10) against a fake browser page — the same construction
`tests/test_job_monitoring_service.py` uses — so `ApplicationStateService`
is exercised against its actual dependency, not a stand-in.
"""

from pathlib import Path

from app.application_planning.decision import DecisionEngine, DecisionThresholds
from app.application_planning.package_builder import ApplicationPackageBuilder
from app.application_planning.planner import ApplicationPlanner
from app.application_planning.service import ApplicationPlanningService
from app.browser_automation.models import FormFieldType, PortalType
from app.browser_automation.portal import GreenhouseAdapter
from app.browser_automation.service import BrowserAutomationService
from app.cover_letter.service import CoverLetterGenerationService
from app.intelligence.resume_planner import ResumePlanner
from app.job_discovery.models import JobProviderName
from app.job_monitoring.deduplication import DuplicateDetector
from app.job_monitoring.dispatcher import JobDispatcher
from app.job_monitoring.filters import MonitoringJobFilter
from app.job_monitoring.history import MonitoringHistoryStore
from app.job_monitoring.models import MonitoringConfig
from app.job_monitoring.monitor import JobMonitor
from app.job_monitoring.service import JobMonitoringService
from app.job_monitoring.watcher import PortalWatcher
from app.resume.service import ResumeGenerationService
from tests.browser_automation_fixtures import FakePage
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.job_monitoring_fixtures import FakeJobProvider
from tests.resume_fixtures import make_llm_service


class FakeBrowserSession:
    def __init__(self, page: FakePage) -> None:
        self._page = page

    async def new_page(self) -> FakePage:
        return self._page


def blueprint():
    return ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())


def planning_service(**decision_kwargs: object) -> ApplicationPlanningService:
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    planner = ApplicationPlanner(
        decision_engine=DecisionEngine(DecisionThresholds(**decision_kwargs))
    )
    return ApplicationPlanningService(planner=planner, package_builder=builder)


def ready_page() -> FakePage:
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    return page


def build_monitoring_service(
    tmp_path: Path,
    jobs: list,
    planning: ApplicationPlanningService,
    with_dispatcher: bool = True,
    page: FakePage | None = None,
) -> JobMonitoringService:
    watcher = PortalWatcher(FakeJobProvider(JobProviderName.GREENHOUSE, jobs=jobs))
    detector = DuplicateDetector(
        history=MonitoringHistoryStore(path=tmp_path / "mon_history.jsonl")
    )
    monitor = JobMonitor([watcher], detector, MonitoringJobFilter())
    config = MonitoringConfig(polling_interval_seconds=0.02)
    dispatcher = None
    if with_dispatcher:
        dispatcher = JobDispatcher(
            planning,
            BrowserAutomationService(),
            FakeBrowserSession(page or ready_page()),
            PortalType.GREENHOUSE,
        )
    return JobMonitoringService(
        monitor, planning, config, dispatcher=dispatcher, deduplicator=detector
    )
