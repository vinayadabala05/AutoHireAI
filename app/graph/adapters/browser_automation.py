"""Adapter: wraps Sprint 10's `BrowserAutomationService` as a `GraphNode`.

Only wraps the existing service's public `submit_application()` method —
no change to `app.browser_automation` at all. The Playwright `Page` is
supplied as a graph input, not owned by this node: browser/page lifecycle
(opening, closing, context reuse) is the caller's responsibility, exactly
as `app.browser_automation.browser.BrowserSession` already models it —
a `GraphNode` should not own a resource with side effects that outlive
one `execute()` call.
"""

from typing import Any

from playwright.async_api import Page

from app.application_planning.models import ApplicationPackage
from app.browser_automation.models import FormFillOptions, PortalType, SubmissionResult
from app.browser_automation.service import BrowserAutomationService
from app.career_profile.models import CareerProfile
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode


class BrowserAutomationNode(GraphNode):
    """Submits an `ApplicationPackage` via `BrowserAutomationService.submit_application()`."""

    def __init__(
        self,
        node_id: str,
        service: BrowserAutomationService,
        portal: PortalType,
        *,
        name: str = "Browser Automation",
        package_input: str = "application_planning",
        page_input: str = "page",
        profile_input: str = "profile",
        options_input: str = "options",
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._portal = portal
        self._package_input = package_input
        self._page_input = page_input
        self._profile_input = profile_input
        self._options_input = options_input

    async def execute(self, context: ExecutionContext) -> SubmissionResult:
        package: ApplicationPackage = resolve_input(context, self._package_input)
        page: Page = resolve_input(context, self._page_input)
        profile: CareerProfile = resolve_input(context, self._profile_input)
        options: FormFillOptions | None = resolve_input(
            context, self._options_input, required=False
        )
        return await self._service.submit_application(
            self._portal, page, package, profile, options=options
        )
