"""Portal adapter architecture: `PortalAdapter` (the extension point) + a
self-registration registry, mirroring Sprint 4/7/8's provider/node
registries (`app.llm.registry`, `app.job_discovery.providers.base`,
`app.graph.registry`).

Adding a fifth portal requires exactly one new class decorated with
`@register_portal(...)` — no change to `navigator.py`, `form_filler.py`,
`uploader.py`, or `executor.py`, all of which depend only on
`PortalAdapterProtocol`.

Selectors below are best-effort, documented defaults for each platform's
*typical* DOM — real employer career pages customize styling/markup, so
production use should expect to override `field_selectors` per posting
where needed. This module never falls back to guessing at unknown
selectors; unknown questions are surfaced by `form_filler.py`, not here.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from playwright.async_api import Page

from app.browser_automation.exceptions import PortalNotSupportedError
from app.browser_automation.models import FormFieldType, PortalType

_PORTAL_REGISTRY: dict[PortalType, type["PortalAdapter"]] = {}


def register_portal(
    portal_type: PortalType,
) -> Callable[[type["PortalAdapter"]], type["PortalAdapter"]]:
    """Class decorator that registers a `PortalAdapter` subclass under `portal_type`."""

    def decorator(adapter_cls: type["PortalAdapter"]) -> type["PortalAdapter"]:
        _PORTAL_REGISTRY[portal_type] = adapter_cls
        return adapter_cls

    return decorator


def get_portal_adapter(portal_type: PortalType) -> "PortalAdapter":
    """Instantiate the adapter registered for `portal_type`.

    Raises `PortalNotSupportedError` if no adapter is registered.
    """
    try:
        return _PORTAL_REGISTRY[portal_type]()
    except KeyError as exc:
        raise PortalNotSupportedError(
            f"No adapter registered for portal '{portal_type.value}'."
        ) from exc


def available_portals() -> list[PortalType]:
    """Every currently registered portal, sorted by name."""
    return sorted(_PORTAL_REGISTRY, key=lambda portal: portal.value)


class PortalAdapter(ABC):
    """Contract every concrete job-portal adapter must implement."""

    @property
    @abstractmethod
    def portal_type(self) -> PortalType: ...

    @property
    @abstractmethod
    def field_selectors(self) -> dict[FormFieldType, str]:
        """Known form-field CSS selectors for this portal's application form."""

    @abstractmethod
    async def is_logged_in(self, page: Page) -> bool:
        """Whether the current page shows the user as authenticated."""

    @abstractmethod
    async def find_apply_button(self, page: Page) -> str | None:
        """The CSS selector of the Apply button/link, or `None` if not present."""

    @abstractmethod
    async def submit(self, page: Page) -> None:
        """Click the final submit control for this portal's application form."""

    @abstractmethod
    async def detect_success(self, page: Page) -> bool:
        """Whether the page indicates the application was submitted successfully."""

    async def extract_application_id(self, page: Page) -> str | None:
        """Best-effort application/confirmation id. `None` if this portal exposes none."""
        return None


@register_portal(PortalType.LINKEDIN)
class LinkedInEasyApplyAdapter(PortalAdapter):
    """LinkedIn Easy Apply — a multi-step modal, not a full page form.

    LinkedIn pre-fills name/email/resume from the member's own profile, so
    those aren't in `field_selectors`; only the fields Easy Apply typically
    asks as extra screening questions are mapped.
    """

    _APPLY_BUTTON_SELECTOR = "button.jobs-apply-button"
    _SUBMIT_SELECTOR = "button[aria-label='Submit application']"
    _NEXT_STEP_SELECTOR = "button[aria-label='Continue to next step']"
    _SUCCESS_SELECTOR = "h3:has-text('Your application was sent')"
    _LOGGED_IN_SELECTOR = "img.global-nav__me-photo"

    _FIELD_SELECTORS: dict[FormFieldType, str] = {
        FormFieldType.PHONE: "input[id*='phoneNumber']",
        FormFieldType.WORK_AUTHORIZATION: "select[id*='workAuthorization']",
        FormFieldType.VISA_SPONSORSHIP: "input[id*='requireVisa']",
        FormFieldType.NOTICE_PERIOD: "input[id*='noticePeriod']",
        FormFieldType.SALARY_EXPECTATION: "input[id*='salary']",
        FormFieldType.RESUME_UPLOAD: "input[name='file']",
        # LinkedIn Easy Apply has no separate cover-letter upload control —
        # cover letters are typically pasted as free text or omitted.
    }

    @property
    def portal_type(self) -> PortalType:
        return PortalType.LINKEDIN

    @property
    def field_selectors(self) -> dict[FormFieldType, str]:
        return dict(self._FIELD_SELECTORS)

    async def is_logged_in(self, page: Page) -> bool:
        return await page.locator(self._LOGGED_IN_SELECTOR).count() > 0

    async def find_apply_button(self, page: Page) -> str | None:
        if await page.locator(self._APPLY_BUTTON_SELECTOR).count() > 0:
            return self._APPLY_BUTTON_SELECTOR
        return None

    async def submit(self, page: Page) -> None:
        if await page.locator(self._NEXT_STEP_SELECTOR).count() > 0:
            await page.click(self._NEXT_STEP_SELECTOR)
        await page.click(self._SUBMIT_SELECTOR)

    async def detect_success(self, page: Page) -> bool:
        return await page.locator(self._SUCCESS_SELECTOR).count() > 0


@register_portal(PortalType.GREENHOUSE)
class GreenhouseAdapter(PortalAdapter):
    """Greenhouse job boards embed the application form directly on the job page."""

    _APPLY_BUTTON_SELECTOR = "a:has-text('Apply for this job')"
    _SUBMIT_SELECTOR = "button#submit_app, input#submit_app"
    _SUCCESS_SELECTOR = "text=Thank you for your interest"
    _LOGGED_IN_SELECTOR = "a:has-text('Sign out')"

    _FIELD_SELECTORS: dict[FormFieldType, str] = {
        FormFieldType.FULL_NAME: "#job_application_first_name",
        FormFieldType.EMAIL: "#job_application_email",
        FormFieldType.PHONE: "#job_application_phone",
        FormFieldType.ADDRESS: "#job_application_location",
        FormFieldType.WORK_AUTHORIZATION: "select[id*='work_authorization']",
        FormFieldType.VISA_SPONSORSHIP: "select[id*='visa_sponsorship']",
        FormFieldType.NOTICE_PERIOD: "input[id*='notice_period']",
        FormFieldType.SALARY_EXPECTATION: "input[id*='salary_expectation']",
        FormFieldType.RESUME_UPLOAD: "input#resume",
        FormFieldType.COVER_LETTER_UPLOAD: "input#cover_letter",
    }

    @property
    def portal_type(self) -> PortalType:
        return PortalType.GREENHOUSE

    @property
    def field_selectors(self) -> dict[FormFieldType, str]:
        return dict(self._FIELD_SELECTORS)

    async def is_logged_in(self, page: Page) -> bool:
        return await page.locator(self._LOGGED_IN_SELECTOR).count() > 0

    async def find_apply_button(self, page: Page) -> str | None:
        if await page.locator(self._APPLY_BUTTON_SELECTOR).count() > 0:
            return self._APPLY_BUTTON_SELECTOR
        return None

    async def submit(self, page: Page) -> None:
        await page.click(self._SUBMIT_SELECTOR)

    async def detect_success(self, page: Page) -> bool:
        return await page.locator(self._SUCCESS_SELECTOR).count() > 0


@register_portal(PortalType.LEVER)
class LeverAdapter(PortalAdapter):
    """Lever job postings link to a separate `/apply` page for the application form."""

    _APPLY_BUTTON_SELECTOR = "a.postings-btn"
    _SUBMIT_SELECTOR = "button.template-btn-submit"
    _SUCCESS_SELECTOR = "text=Thank you for applying"
    _LOGGED_IN_SELECTOR = "a:has-text('Log out')"

    _FIELD_SELECTORS: dict[FormFieldType, str] = {
        FormFieldType.FULL_NAME: "input[name='name']",
        FormFieldType.EMAIL: "input[name='email']",
        FormFieldType.PHONE: "input[name='phone']",
        FormFieldType.ADDRESS: "input[name='location']",
        FormFieldType.WORK_AUTHORIZATION: "select[name*='work_authorization']",
        FormFieldType.VISA_SPONSORSHIP: "select[name*='visa']",
        FormFieldType.NOTICE_PERIOD: "input[name*='notice_period']",
        FormFieldType.SALARY_EXPECTATION: "input[name*='salary']",
        FormFieldType.RESUME_UPLOAD: "input[name='resume']",
        FormFieldType.COVER_LETTER_UPLOAD: "input[name='coverLetter']",
    }

    @property
    def portal_type(self) -> PortalType:
        return PortalType.LEVER

    @property
    def field_selectors(self) -> dict[FormFieldType, str]:
        return dict(self._FIELD_SELECTORS)

    async def is_logged_in(self, page: Page) -> bool:
        return await page.locator(self._LOGGED_IN_SELECTOR).count() > 0

    async def find_apply_button(self, page: Page) -> str | None:
        if await page.locator(self._APPLY_BUTTON_SELECTOR).count() > 0:
            return self._APPLY_BUTTON_SELECTOR
        return None

    async def submit(self, page: Page) -> None:
        await page.click(self._SUBMIT_SELECTOR)

    async def detect_success(self, page: Page) -> bool:
        return await page.locator(self._SUCCESS_SELECTOR).count() > 0


@register_portal(PortalType.ASHBY)
class AshbyAdapter(PortalAdapter):
    """Ashby job boards render the application form in-page via a JS app."""

    _APPLY_BUTTON_SELECTOR = "button:has-text('Apply for this Job')"
    _SUBMIT_SELECTOR = "button:has-text('Submit Application')"
    _SUCCESS_SELECTOR = "text=Your application has been submitted"
    _LOGGED_IN_SELECTOR = "button:has-text('Sign out')"

    _FIELD_SELECTORS: dict[FormFieldType, str] = {
        FormFieldType.FULL_NAME: "input[name='name']",
        FormFieldType.EMAIL: "input[name='email']",
        FormFieldType.PHONE: "input[name='phone']",
        FormFieldType.ADDRESS: "input[name='location']",
        FormFieldType.WORK_AUTHORIZATION: "select[name*='workAuthorization']",
        FormFieldType.VISA_SPONSORSHIP: "input[name*='visaSponsorship']",
        FormFieldType.NOTICE_PERIOD: "input[name*='noticePeriod']",
        FormFieldType.SALARY_EXPECTATION: "input[name*='compensation']",
        FormFieldType.RESUME_UPLOAD: "input[name='resume']",
        FormFieldType.COVER_LETTER_UPLOAD: "input[name='coverLetter']",
    }

    @property
    def portal_type(self) -> PortalType:
        return PortalType.ASHBY

    @property
    def field_selectors(self) -> dict[FormFieldType, str]:
        return dict(self._FIELD_SELECTORS)

    async def is_logged_in(self, page: Page) -> bool:
        return await page.locator(self._LOGGED_IN_SELECTOR).count() > 0

    async def find_apply_button(self, page: Page) -> str | None:
        if await page.locator(self._APPLY_BUTTON_SELECTOR).count() > 0:
            return self._APPLY_BUTTON_SELECTOR
        return None

    async def submit(self, page: Page) -> None:
        await page.click(self._SUBMIT_SELECTOR)

    async def detect_success(self, page: Page) -> bool:
        return await page.locator(self._SUCCESS_SELECTOR).count() > 0
