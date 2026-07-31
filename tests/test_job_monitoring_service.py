"""Integration tests for `app.job_monitoring.service.JobMonitoringService`."""

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
from app.job_monitoring.models import MonitoringConfig, ProcessingOutcome
from app.job_monitoring.monitor import JobMonitor
from app.job_monitoring.service import JobMonitoringService
from app.job_monitoring.watcher import PortalWatcher
from app.resume.service import ResumeGenerationService
from tests.browser_automation_fixtures import FakePage
from tests.cover_letter_fixtures import make_llm_service as make_cover_letter_llm_service
from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
from tests.job_discovery_fixtures import sample_job
from tests.job_monitoring_fixtures import FakeJobProvider
from tests.resume_fixtures import make_llm_service, sample_career_profile


class _FakeBrowserSession:
    def __init__(self, page: FakePage) -> None:
        self._page = page

    async def new_page(self) -> FakePage:
        return self._page


def _blueprint():
    return ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())


def _planning_service(**decision_kwargs: object) -> ApplicationPlanningService:
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_cover_letter_llm_service([])),
        enhance_with_llm=False,
    )
    planner = ApplicationPlanner(
        decision_engine=DecisionEngine(DecisionThresholds(**decision_kwargs))
    )
    return ApplicationPlanningService(planner=planner, package_builder=builder)


def _ready_page() -> FakePage:
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    return page


def _build_service(
    tmp_path: Path,
    jobs: list,
    planning_service: ApplicationPlanningService,
    with_dispatcher: bool = True,
) -> JobMonitoringService:
    watcher = PortalWatcher(FakeJobProvider(JobProviderName.GREENHOUSE, jobs=jobs))
    detector = DuplicateDetector(history=MonitoringHistoryStore(path=tmp_path / "history.jsonl"))
    monitor = JobMonitor([watcher], detector, MonitoringJobFilter())
    config = MonitoringConfig(polling_interval_seconds=0.02)
    dispatcher = None
    if with_dispatcher:
        dispatcher = JobDispatcher(
            planning_service,
            BrowserAutomationService(),
            _FakeBrowserSession(_ready_page()),
            PortalType.GREENHOUSE,
        )
    return JobMonitoringService(
        monitor, planning_service, config, dispatcher=dispatcher, deduplicator=detector
    )


async def test_scan_once_discovers_and_submits(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], _planning_service())

    result = await service.scan_once(profile=sample_career_profile(), blueprint=_blueprint())

    assert result.jobs_discovered == 1
    assert result.jobs_new == 1
    assert result.jobs_submitted == 1
    assert result.jobs_failed == 0
    assert result.latency_ms is not None


async def test_scan_once_second_run_sees_duplicate(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], _planning_service())

    await service.scan_once(profile=sample_career_profile(), blueprint=_blueprint())
    result = await service.scan_once(profile=sample_career_profile(), blueprint=_blueprint())

    assert result.jobs_duplicate == 1
    assert result.jobs_new == 0


async def test_scan_once_records_statistics(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], _planning_service())

    await service.scan_once(profile=sample_career_profile(), blueprint=_blueprint())
    stats = service.get_statistics()

    assert stats.total_scans == 1
    assert stats.total_jobs_submitted == 1
    assert stats.last_scan_at is not None


async def test_scan_once_with_low_match_score_skips_without_dispatch(tmp_path: Path) -> None:
    job = sample_job(skills=["Rust", "Go", "Elixir"])
    strict_planning = _planning_service(apply_score_threshold=99.9)
    service = _build_service(tmp_path, [job], strict_planning)

    result = await service.scan_once(profile=sample_career_profile(), blueprint=_blueprint())

    assert result.jobs_skipped == 1
    assert result.jobs_submitted == 0


async def test_scan_once_without_profile_does_not_dispatch(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job], _planning_service())

    result = await service.scan_once()  # no profile supplied

    assert result.jobs_new == 1
    assert result.jobs_submitted == 0
    assert result.processed_jobs == []


async def test_process_job_without_dispatcher_marks_skipped(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], _planning_service(), with_dispatcher=False)

    processed = await service.process_job(job, sample_career_profile(), _blueprint())
    assert processed.outcome is ProcessingOutcome.SKIPPED
    assert "no dispatcher" in (processed.detail or "").lower()


async def test_process_job_marks_failed_when_dispatch_raises(tmp_path: Path) -> None:
    from tests.resume_fixtures import profile_with_no_skills

    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    # apply_score_threshold=0 guarantees an APPLY decision regardless of
    # match score, so `process_job` reaches `dispatch()`; the empty-skills
    # profile then makes `ApplicationPlanningNode` fail *inside* the
    # dispatch graph (resume generation requires at least one skill),
    # so `JobDispatcher.dispatch()` raises `DispatchError` — exactly what
    # `process_job()`'s except branch handles.
    lenient_planning_service = _planning_service(apply_score_threshold=0.0)
    service = _build_service(tmp_path, [job], lenient_planning_service)

    processed = await service.process_job(job, profile_with_no_skills(), _blueprint())
    assert processed.outcome is ProcessingOutcome.FAILED


async def test_scan_once_records_error_when_monitor_scan_raises(tmp_path: Path) -> None:
    job = sample_job()
    service = _build_service(tmp_path, [job], _planning_service())

    async def _boom(config, profile=None):  # noqa: ANN001
        raise RuntimeError("monitor exploded")

    service._monitor.scan = _boom  # type: ignore[method-assign]  # noqa: SLF001

    result = await service.scan_once(profile=sample_career_profile())
    assert result.errors == ["monitor exploded"]
    assert result.ended_at is not None


async def test_process_jobs_runs_concurrently_and_bounded(tmp_path: Path) -> None:
    jobs = [
        sample_job(source_url=f"https://x/{i}", skills=["Python", "FastAPI", "PostgreSQL"])
        for i in range(3)
    ]
    service = _build_service(tmp_path, jobs, _planning_service())
    service.config.max_concurrent_processing = 2

    processed = await service.process_jobs(jobs, sample_career_profile(), _blueprint())
    assert len(processed) == 3
    assert all(p.outcome is ProcessingOutcome.SUBMITTED for p in processed)


async def test_start_and_stop_monitoring_runs_scheduled_scans(tmp_path: Path) -> None:
    job = sample_job(skills=["Python", "FastAPI", "PostgreSQL"])
    service = _build_service(tmp_path, [job], _planning_service())

    import asyncio

    await service.start_monitoring(sample_career_profile(), _blueprint())
    assert service.is_running is True
    await asyncio.sleep(0.05)
    await service.stop_monitoring()

    assert service.is_running is False
    assert service.get_statistics().total_scans >= 1
