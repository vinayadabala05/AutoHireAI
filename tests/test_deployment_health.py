"""Unit tests for `deployment.health`."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import deployment.health as health_module
from app.core.settings import settings
from deployment.health import ReadinessReport, build_readiness_report, build_readiness_router


class _FakeRedisClient:
    def __init__(self, *, healthy: bool = True) -> None:
        self._healthy = healthy
        self.aclose_called = False

    async def ping(self) -> bool:
        if not self._healthy:
            raise ConnectionError("redis unreachable")
        return True

    async def aclose(self) -> None:
        self.aclose_called = True


def test_readiness_report_is_ready_only_when_status_ok() -> None:
    assert ReadinessReport(status=health_module.HealthStatus.OK).is_ready is True
    assert ReadinessReport(status=health_module.HealthStatus.DOWN).is_ready is False


async def test_check_redis_connection_true_when_ping_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeRedisClient(healthy=True)
    monkeypatch.setattr(
        health_module.Redis, "from_url", lambda *a, **k: fake_client
    )  # noqa: ARG005

    assert await health_module.check_redis_connection(settings, timeout_seconds=1.0) is True
    assert fake_client.aclose_called is True


async def test_check_redis_connection_false_when_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeRedisClient(healthy=False)
    monkeypatch.setattr(
        health_module.Redis, "from_url", lambda *a, **k: fake_client
    )  # noqa: ARG005

    assert await health_module.check_redis_connection(settings, timeout_seconds=1.0) is False


async def test_build_readiness_report_ok_when_all_checks_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_module, "check_database_connection", _ok)
    monkeypatch.setattr(health_module, "check_redis_connection", _ok_with_args)

    report = await build_readiness_report(settings, timeout_seconds=1.0)
    assert report.is_ready is True
    assert report.checks == {"database": True, "redis": True}


async def test_build_readiness_report_down_when_one_check_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_module, "check_database_connection", _ok)
    monkeypatch.setattr(health_module, "check_redis_connection", _fail_with_args)

    report = await build_readiness_report(settings, timeout_seconds=1.0)
    assert report.is_ready is False
    assert report.checks == {"database": True, "redis": False}


async def test_build_readiness_report_handles_raising_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_module, "check_database_connection", _boom)
    monkeypatch.setattr(health_module, "check_redis_connection", _ok_with_args)

    report = await build_readiness_report(settings, timeout_seconds=1.0)
    assert report.checks["database"] is False


def test_readiness_router_returns_200_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_module, "check_database_connection", _ok)
    monkeypatch.setattr(health_module, "check_redis_connection", _ok_with_args)

    app = FastAPI()
    app.include_router(build_readiness_router(settings, timeout_seconds=1.0))
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_router_returns_503_when_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_module, "check_database_connection", _fail)
    monkeypatch.setattr(health_module, "check_redis_connection", _ok_with_args)

    app = FastAPI()
    app.include_router(build_readiness_router(settings, timeout_seconds=1.0))
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 503


async def _ok() -> bool:
    return True


async def _fail() -> bool:
    return False


async def _boom() -> bool:
    raise RuntimeError("database exploded")


async def _ok_with_args(*args: object, **kwargs: object) -> bool:
    return True


async def _fail_with_args(*args: object, **kwargs: object) -> bool:
    return False
