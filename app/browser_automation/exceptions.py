"""Exception hierarchy for the Browser Automation Engine.

Mirrors every prior sprint's convention: one base class, specific
subclasses so callers can catch broadly or narrowly.
"""


class BrowserAutomationError(Exception):
    """Base class for every exception raised by `app.browser_automation`."""


class PortalNotSupportedError(BrowserAutomationError):
    """Raised when no adapter is registered for a requested portal."""


class LoginError(BrowserAutomationError):
    """Raised when authentication with a portal fails."""


class SessionExpiredError(BrowserAutomationError):
    """Raised when a persisted session is no longer valid and re-login is required."""


class NavigationError(BrowserAutomationError):
    """Raised when opening a job page, finding the Apply button, or a redirect fails."""


class FormFillError(BrowserAutomationError):
    """Raised when a required form field cannot be filled."""


class UploadError(BrowserAutomationError):
    """Raised when a document upload cannot be verified as successful."""


class SubmissionError(BrowserAutomationError):
    """Raised when submitting the application fails or success cannot be confirmed."""


class UnsupportedQuestionError(BrowserAutomationError):
    """Raised when a caller demands a fully-answered form but unsupported questions remain."""
