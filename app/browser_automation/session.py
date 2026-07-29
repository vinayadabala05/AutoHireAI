"""Session persistence: save/load Playwright `storage_state`, and validate reuse.

Stores each portal/account's cookies + local storage as one JSON file
(Playwright's own `storage_state` format) under `data/browser_sessions/`,
mirroring the `data/<subsystem>/` on-disk convention Sprint 3.5/5/6/7 use.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.browser_automation.exceptions import SessionExpiredError
from app.browser_automation.interfaces import PortalAdapterProtocol
from app.browser_automation.models import PortalType, SessionData

_DEFAULT_SESSION_DIR = Path("data/browser_sessions")
_DEFAULT_SESSION_TTL = timedelta(days=7)


class SessionStore:
    def __init__(
        self,
        directory: Path | str = _DEFAULT_SESSION_DIR,
        ttl: timedelta = _DEFAULT_SESSION_TTL,
    ) -> None:
        self._directory = Path(directory)
        self._ttl = ttl

    async def save(
        self, portal: PortalType, account_key: str, context: BrowserContext
    ) -> SessionData:
        path = self._path_for(portal, account_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(path))
        now = datetime.now(UTC)
        session = SessionData(
            portal=portal,
            account_key=account_key,
            storage_state_path=str(path),
            saved_at=now,
            expires_at=now + self._ttl,
        )
        logger.bind(portal=portal.value, account_key=account_key).info("Saved browser session.")
        return session

    def load(self, portal: PortalType, account_key: str) -> SessionData | None:
        """Load persisted session metadata, or `None` if nothing was ever saved."""
        path = self._path_for(portal, account_key)
        if not path.exists():
            return None
        saved_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        return SessionData(
            portal=portal,
            account_key=account_key,
            storage_state_path=str(path),
            saved_at=saved_at,
            expires_at=saved_at + self._ttl,
        )

    def is_expired(self, session: SessionData) -> bool:
        return session.expires_at is not None and datetime.now(UTC) >= session.expires_at

    def delete(self, portal: PortalType, account_key: str) -> None:
        self._path_for(portal, account_key).unlink(missing_ok=True)

    async def validate(
        self, session: SessionData, page: Page, adapter: PortalAdapterProtocol
    ) -> bool:
        """Check a session is both unexpired and still actually authenticated.

        Raises `SessionExpiredError` if past its TTL; otherwise defers to
        the portal adapter's own `is_logged_in()` — a TTL alone can't tell
        you a portal didn't revoke the session server-side.
        """
        if self.is_expired(session):
            raise SessionExpiredError(
                f"Session for {session.portal.value}/{session.account_key} has expired."
            )
        return await adapter.is_logged_in(page)

    def _path_for(self, portal: PortalType, account_key: str) -> Path:
        return self._directory / portal.value / f"{account_key}.json"
