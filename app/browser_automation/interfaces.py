"""Structural interfaces for the Browser Automation Engine.

`PortalAdapterProtocol` is the extension point: a new job portal only
needs a class satisfying this shape (plus self-registration — see
`portal.py`) to plug into `ApplicationExecutor`/`BrowserAutomationService`
with no change to navigation, form-filling, upload, or submission code.
"""

from typing import Protocol

from playwright.async_api import Page

from app.browser_automation.models import FormFieldType, PortalType


class PortalAdapterProtocol(Protocol):
    @property
    def portal_type(self) -> PortalType: ...

    @property
    def field_selectors(self) -> dict[FormFieldType, str]: ...

    async def is_logged_in(self, page: Page) -> bool: ...
    async def find_apply_button(self, page: Page) -> str | None: ...
    async def submit(self, page: Page) -> None: ...
    async def detect_success(self, page: Page) -> bool: ...
    async def extract_application_id(self, page: Page) -> str | None: ...
