"""Browser Automation Engine.

Receives an `ApplicationPackage` (Sprint 9) and submits it on a supported
job portal (LinkedIn Easy Apply, Greenhouse, Lever, Ashby) via Playwright.
`BrowserAutomationService` is the single entrypoint callers should use.

This supersedes the Sprint 1 `app/browser/` placeholder package (never
implemented) — that package is left untouched; this is the real
implementation, under its own name to avoid any ambiguity.
"""

from app.browser_automation.browser import BrowserSession
from app.browser_automation.exceptions import (
    BrowserAutomationError,
    FormFillError,
    LoginError,
    NavigationError,
    PortalNotSupportedError,
    SessionExpiredError,
    SubmissionError,
    UnsupportedQuestionError,
    UploadError,
)
from app.browser_automation.executor import ApplicationExecutor
from app.browser_automation.form_filler import FormFiller
from app.browser_automation.models import (
    BrowserConfig,
    FormFieldType,
    FormFillOptions,
    FormFillResult,
    LoginCredentials,
    PortalType,
    QuestionInputType,
    SessionData,
    SubmissionResult,
    SubmissionStatus,
    UnsupportedQuestion,
    UploadResult,
)
from app.browser_automation.navigator import Navigator
from app.browser_automation.playwright_manager import PlaywrightManager
from app.browser_automation.portal import PortalAdapter, available_portals, get_portal_adapter
from app.browser_automation.service import BrowserAutomationService
from app.browser_automation.session import SessionStore
from app.browser_automation.uploader import DocumentUploader

__all__ = [
    "ApplicationExecutor",
    "BrowserAutomationError",
    "BrowserAutomationService",
    "BrowserConfig",
    "BrowserSession",
    "DocumentUploader",
    "FormFieldType",
    "FormFillError",
    "FormFillOptions",
    "FormFillResult",
    "FormFiller",
    "LoginCredentials",
    "LoginError",
    "NavigationError",
    "Navigator",
    "PlaywrightManager",
    "PortalAdapter",
    "PortalNotSupportedError",
    "PortalType",
    "QuestionInputType",
    "SessionData",
    "SessionExpiredError",
    "SessionStore",
    "SubmissionError",
    "SubmissionResult",
    "SubmissionStatus",
    "UnsupportedQuestion",
    "UnsupportedQuestionError",
    "UploadError",
    "UploadResult",
    "available_portals",
    "get_portal_adapter",
]
