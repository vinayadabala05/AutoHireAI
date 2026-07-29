"""Unit tests for `app.browser_automation.session.SessionStore`."""

from datetime import timedelta
from pathlib import Path

import pytest

from app.browser_automation.exceptions import SessionExpiredError
from app.browser_automation.models import PortalType
from app.browser_automation.session import SessionStore
from tests.browser_automation_fixtures import FakeBrowserContext, FakePage


class _FakeAdapter:
    def __init__(self, logged_in: bool) -> None:
        self._logged_in = logged_in

    async def is_logged_in(self, page: FakePage) -> bool:
        return self._logged_in


async def test_save_writes_storage_state_file(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    context = FakeBrowserContext()
    session = await store.save(PortalType.GREENHOUSE, "acct1", context)
    assert Path(session.storage_state_path).exists()
    assert session.portal is PortalType.GREENHOUSE
    assert session.account_key == "acct1"


async def test_load_returns_none_when_never_saved(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    assert store.load(PortalType.LEVER, "acct1") is None


async def test_load_returns_session_after_save(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    context = FakeBrowserContext()
    await store.save(PortalType.ASHBY, "acct1", context)
    loaded = store.load(PortalType.ASHBY, "acct1")
    assert loaded is not None
    assert loaded.account_key == "acct1"


def test_is_expired_false_for_fresh_session(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from app.browser_automation.models import SessionData

    store = SessionStore(directory=tmp_path)
    session = SessionData(
        portal=PortalType.LINKEDIN,
        account_key="acct1",
        storage_state_path=str(tmp_path / "x.json"),
        saved_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    assert store.is_expired(session) is False


def test_is_expired_true_for_past_expiry(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from app.browser_automation.models import SessionData

    store = SessionStore(directory=tmp_path)
    session = SessionData(
        portal=PortalType.LINKEDIN,
        account_key="acct1",
        storage_state_path=str(tmp_path / "x.json"),
        saved_at=datetime.now(UTC) - timedelta(days=10),
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    assert store.is_expired(session) is True


def test_is_expired_false_when_no_expiry_set(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from app.browser_automation.models import SessionData

    store = SessionStore(directory=tmp_path)
    session = SessionData(
        portal=PortalType.LINKEDIN,
        account_key="acct1",
        storage_state_path=str(tmp_path / "x.json"),
        saved_at=datetime.now(UTC),
        expires_at=None,
    )
    assert store.is_expired(session) is False


async def test_delete_removes_saved_session(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    context = FakeBrowserContext()
    await store.save(PortalType.GREENHOUSE, "acct1", context)
    store.delete(PortalType.GREENHOUSE, "acct1")
    assert store.load(PortalType.GREENHOUSE, "acct1") is None


def test_delete_unknown_session_is_a_no_op(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    store.delete(PortalType.GREENHOUSE, "missing")  # should not raise


async def test_validate_raises_when_expired(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path, ttl=timedelta(seconds=-1))
    context = FakeBrowserContext()
    session = await store.save(PortalType.GREENHOUSE, "acct1", context)
    with pytest.raises(SessionExpiredError):
        await store.validate(session, FakePage(), _FakeAdapter(logged_in=True))


async def test_validate_defers_to_adapter_is_logged_in(tmp_path: Path) -> None:
    store = SessionStore(directory=tmp_path)
    context = FakeBrowserContext()
    session = await store.save(PortalType.GREENHOUSE, "acct1", context)
    assert await store.validate(session, FakePage(), _FakeAdapter(logged_in=True)) is True
    assert await store.validate(session, FakePage(), _FakeAdapter(logged_in=False)) is False
