"""Browser Automation Service: the single entrypoint every caller should use.

Orchestrates `PlaywrightManager`, `SessionStore`, `Navigator`,
`FormFiller`, `DocumentUploader`, and `ApplicationExecutor`, mirroring the
"one facade per subsystem" convention every prior sprint established
(`CareerProfileService`, `LLMService`, ..., `ApplicationPlanningService`).
"""

from playwright.async_api import Page

from app.application_planning.models import ApplicationPackage, ApplicationPlan
from app.browser_automation.exceptions import LoginError
from app.browser_automation.executor import ApplicationExecutor
from app.browser_automation.form_filler import FormFiller
from app.browser_automation.models import (
    FormFillOptions,
    FormFillResult,
    LoginCredentials,
    PortalType,
    SessionData,
    SubmissionResult,
    UploadResult,
)
from app.browser_automation.navigator import Navigator
from app.browser_automation.playwright_manager import PlaywrightManager
from app.browser_automation.portal import get_portal_adapter
from app.browser_automation.session import SessionStore
from app.browser_automation.uploader import DocumentUploader
from app.career_profile.models import CareerProfile
from app.job_discovery.models import DiscoveredJob

_LOGIN_EMAIL_SELECTOR = "input[type=email], input[name=username]"
_LOGIN_PASSWORD_SELECTOR = "input[type=password]"
_LOGIN_SUBMIT_SELECTOR = "button[type=submit]"


class BrowserAutomationService:
    def __init__(
        self,
        manager: PlaywrightManager | None = None,
        session_store: SessionStore | None = None,
        navigator: Navigator | None = None,
        form_filler: FormFiller | None = None,
        uploader: DocumentUploader | None = None,
        executor: ApplicationExecutor | None = None,
    ) -> None:
        self._manager = manager or PlaywrightManager()
        self._session_store = session_store or SessionStore()
        self._navigator = navigator or Navigator()
        self._form_filler = form_filler or FormFiller()
        self._uploader = uploader or DocumentUploader()
        self._executor = executor or ApplicationExecutor(
            self._navigator, self._form_filler, self._uploader
        )

    async def login(
        self,
        portal: PortalType,
        account_key: str,
        credentials: LoginCredentials,
        login_url: str,
    ) -> SessionData:
        """Log in to `portal` and persist the resulting session for reuse.

        `credentials` is always supplied by the caller (env var, secrets
        manager, interactive prompt, ...) — nothing in this module ever
        embeds a real username/password.
        """
        context = await self._manager.new_context()
        page = await context.new_page()
        try:
            await self._navigator.open_job_page(page, login_url)
            await page.fill(_LOGIN_EMAIL_SELECTOR, credentials.username)
            await page.fill(_LOGIN_PASSWORD_SELECTOR, credentials.password.get_secret_value())
            async with page.expect_navigation():
                await page.click(_LOGIN_SUBMIT_SELECTOR)

            adapter = get_portal_adapter(portal)
            if not await adapter.is_logged_in(page):
                raise LoginError(f"Login to '{portal.value}' did not succeed.")

            return await self._session_store.save(portal, account_key, context)
        finally:
            await context.close()

    async def validate_session(self, portal: PortalType, account_key: str, page: Page) -> bool:
        """Whether a persisted session for `portal`/`account_key` is still usable.

        Returns `False` (rather than raising) when no session was ever
        saved; raises `SessionExpiredError` only once a session exists but
        has passed its TTL — see `SessionStore.validate()`.
        """
        session = self._session_store.load(portal, account_key)
        if session is None:
            return False
        adapter = get_portal_adapter(portal)
        return await self._session_store.validate(session, page, adapter)

    async def fill_application(
        self,
        portal: PortalType,
        page: Page,
        profile: CareerProfile,
        options: FormFillOptions | None = None,
    ) -> FormFillResult:
        adapter = get_portal_adapter(portal)
        return await self._form_filler.fill(page, adapter, profile, options)

    async def upload_documents(
        self, portal: PortalType, page: Page, package: ApplicationPackage
    ) -> list[UploadResult]:
        adapter = get_portal_adapter(portal)
        return await self._uploader.upload_all(page, adapter, package)

    async def submit_application(
        self,
        portal: PortalType,
        page: Page,
        package: ApplicationPackage,
        profile: CareerProfile,
        options: FormFillOptions | None = None,
        plan: ApplicationPlan | None = None,
        job: DiscoveredJob | None = None,
    ) -> SubmissionResult:
        """Run the full navigate -> fill -> upload -> submit flow for one job.

        `plan` and `job` are optional context only (surfaced in the
        result's `metadata`, e.g. the plan's priority or the job's
        location) — everything required to actually submit lives in
        `package` and `profile`.
        """
        adapter = get_portal_adapter(portal)
        result = await self._executor.execute(page, adapter, package, profile, options)
        if plan is not None:
            result.metadata["priority"] = plan.priority.value
            result.metadata["match_score"] = plan.match_score
        if job is not None:
            result.metadata["job_location"] = job.location
        return result
