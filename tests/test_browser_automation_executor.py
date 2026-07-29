"""Unit tests for `app.browser_automation.executor.ApplicationExecutor`."""

from pathlib import Path

from app.browser_automation.executor import ApplicationExecutor
from app.browser_automation.models import FormFieldType, SubmissionStatus
from app.browser_automation.portal import GreenhouseAdapter
from app.graph.retry import FixedDelayRetryPolicy, NoRetryPolicy
from tests.browser_automation_fixtures import FakePage
from tests.resume_fixtures import sample_career_profile


async def _package():
    from app.application_planning.package_builder import ApplicationPackageBuilder
    from app.cover_letter.service import CoverLetterGenerationService
    from app.intelligence.resume_planner import ResumePlanner
    from app.resume.service import ResumeGenerationService
    from tests.intelligence_fixtures import SAMPLE_JOBS, sample_career_context
    from tests.job_discovery_fixtures import sample_job
    from tests.resume_fixtures import make_llm_service

    blueprint = ResumePlanner().plan(SAMPLE_JOBS["backend_engineer"], sample_career_context())
    profile = sample_career_profile()
    builder = ApplicationPackageBuilder(
        ResumeGenerationService(make_llm_service([])),
        CoverLetterGenerationService(make_llm_service([])),
        enhance_with_llm=False,
    )
    return await builder.build(sample_job(), profile, blueprint, "job-1")


def _make_page_ready_for_success(adapter: GreenhouseAdapter) -> FakePage:
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts["text=Thank you for your interest"] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    return page


async def test_execute_returns_submitted_on_full_success(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = _make_page_ready_for_success(adapter)
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.SUBMITTED
    assert result.error_message is None
    assert result.screenshot_path is None


async def test_execute_returns_partial_when_unsupported_questions_remain(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = _make_page_ready_for_success(adapter)
    page.selector_counts[adapter.field_selectors[FormFieldType.WORK_AUTHORIZATION]] = 1
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.PARTIAL
    assert result.metadata["unsupported_questions"]


async def test_execute_returns_failed_and_screenshots_on_navigation_error(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.raise_on_goto = True
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.FAILED
    assert result.error_message is not None
    assert result.screenshot_path is not None
    assert Path(result.screenshot_path).exists()


async def test_execute_returns_failed_when_apply_button_missing(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.FAILED
    assert "Apply button" in result.error_message


async def test_execute_returns_failed_when_success_not_detected(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()
    page.selector_counts[adapter._APPLY_BUTTON_SELECTOR] = 1  # noqa: SLF001
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.FAILED
    assert "confirmed" in result.error_message


async def test_execute_retries_transient_navigation_failures(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = _make_page_ready_for_success(adapter)
    page.goto_fail_times = 1  # fails once, then succeeds on retry
    package = await _package()
    executor = ApplicationExecutor(
        screenshot_dir=tmp_path, retry_policy=FixedDelayRetryPolicy(0.0, max_retries=2)
    )

    result = await executor.execute(page, adapter, package, sample_career_profile())
    assert result.status is SubmissionStatus.SUBMITTED
    assert len(page.goto_calls) == 2


async def test_execute_uses_no_retry_policy_by_default(tmp_path: Path) -> None:
    executor = ApplicationExecutor(screenshot_dir=tmp_path)
    assert isinstance(executor._retry_policy, NoRetryPolicy)  # noqa: SLF001


async def test_execute_uploads_documents_when_selectors_present(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = _make_page_ready_for_success(adapter)
    page.selector_counts[adapter.field_selectors[FormFieldType.RESUME_UPLOAD]] = 1
    page.selector_counts[adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD]] = 1
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.SUBMITTED
    assert adapter.field_selectors[FormFieldType.RESUME_UPLOAD] in page.uploaded_files
    assert adapter.field_selectors[FormFieldType.COVER_LETTER_UPLOAD] in page.uploaded_files


async def test_execute_captures_application_id_when_available(tmp_path: Path) -> None:
    class _AdapterWithId(GreenhouseAdapter):
        async def extract_application_id(self, page: FakePage) -> str:
            return "app-123"

    adapter = _AdapterWithId()
    page = _make_page_ready_for_success(adapter)
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())
    assert result.application_id == "app-123"


async def test_execute_tolerates_screenshot_capture_failure(tmp_path: Path) -> None:
    adapter = GreenhouseAdapter()
    page = FakePage()  # will fail before submission

    async def _boom(path: str) -> None:
        raise RuntimeError("disk full")

    page.screenshot = _boom  # type: ignore[method-assign]
    package = await _package()
    executor = ApplicationExecutor(screenshot_dir=tmp_path)

    result = await executor.execute(page, adapter, package, sample_career_profile())

    assert result.status is SubmissionStatus.FAILED
    assert result.screenshot_path is None
