"""`ApplicationExecutor`: runs one end-to-end application submission.

Orchestrates navigation, form filling, document upload, and submission
for a single job, wrapping each step in `retry_action` (`retry.py`,
reusing Sprint 8's `RetryPolicy` hierarchy) and capturing a screenshot on
any unrecoverable failure. Never raises for a normal submission failure —
it always returns a `SubmissionResult`, with `status=FAILED` and
`error_message` set, so a caller processing many jobs doesn't need a
try/except per job.
"""

from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from playwright.async_api import Page

from app.application_planning.models import ApplicationPackage
from app.browser_automation.exceptions import SubmissionError
from app.browser_automation.form_filler import FormFiller
from app.browser_automation.interfaces import PortalAdapterProtocol
from app.browser_automation.models import FormFillOptions, SubmissionResult, SubmissionStatus
from app.browser_automation.navigator import Navigator
from app.browser_automation.retry import retry_action
from app.browser_automation.uploader import DocumentUploader
from app.career_profile.models import CareerProfile
from app.graph.retry import NoRetryPolicy, RetryPolicy

_DEFAULT_SCREENSHOT_DIR = Path("data/browser_screenshots")


class ApplicationExecutor:
    def __init__(
        self,
        navigator: Navigator | None = None,
        form_filler: FormFiller | None = None,
        uploader: DocumentUploader | None = None,
        retry_policy: RetryPolicy | None = None,
        screenshot_dir: Path | str = _DEFAULT_SCREENSHOT_DIR,
    ) -> None:
        self._navigator = navigator or Navigator()
        self._form_filler = form_filler or FormFiller()
        self._uploader = uploader or DocumentUploader()
        self._retry_policy = retry_policy or NoRetryPolicy()
        self._screenshot_dir = Path(screenshot_dir)

    async def execute(
        self,
        page: Page,
        adapter: PortalAdapterProtocol,
        package: ApplicationPackage,
        profile: CareerProfile,
        options: FormFillOptions | None = None,
    ) -> SubmissionResult:
        try:
            await retry_action(
                lambda: self._navigator.open_job_page(page, package.application_url),
                self._retry_policy,
                "open_job_page",
            )
            await retry_action(
                lambda: self._navigator.click_apply(page, adapter), self._retry_policy, "click_apply"
            )

            fill_result = await self._form_filler.fill(page, adapter, profile, options)
            await self._uploader.upload_all(page, adapter, package)

            await retry_action(lambda: adapter.submit(page), self._retry_policy, "submit")

            if not await adapter.detect_success(page):
                raise SubmissionError("Submission could not be confirmed as successful.")

            application_id = await adapter.extract_application_id(page)
            status = (
                SubmissionStatus.SUBMITTED if fill_result.is_complete else SubmissionStatus.PARTIAL
            )
            logger.bind(job_id=package.job_id, portal=adapter.portal_type.value).info(
                "Application submitted: {}", status.value
            )
            return SubmissionResult(
                status=status,
                portal=adapter.portal_type,
                company=package.company,
                job_id=package.job_id,
                application_url=page.url,
                application_id=application_id,
                submitted_at=datetime.now(UTC),
                metadata={
                    "unsupported_questions": [
                        question.model_dump() for question in fill_result.unsupported_questions
                    ]
                },
            )
        except Exception as exc:
            screenshot_path = await self._capture_screenshot(page, package.job_id)
            logger.bind(job_id=package.job_id, portal=adapter.portal_type.value).error(
                "Application submission failed: {}", exc
            )
            return SubmissionResult(
                status=SubmissionStatus.FAILED,
                portal=adapter.portal_type,
                company=package.company,
                job_id=package.job_id,
                application_url=package.application_url,
                submitted_at=datetime.now(UTC),
                screenshot_path=screenshot_path,
                error_message=str(exc),
            )

    async def _capture_screenshot(self, page: Page, job_id: str) -> str | None:
        try:
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = self._screenshot_dir / f"{job_id}_{datetime.now(UTC):%Y%m%d%H%M%S}.png"
            await page.screenshot(path=str(path))
            return str(path)
        except Exception as exc:
            logger.warning("Failed to capture failure screenshot: {}", exc)
            return None
