"""Unit tests for `deployment.startup.create_production_app`."""

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings
from deployment.config import ConfigurationError
from deployment.settings import DeploymentSettings
from deployment.startup import create_production_app


def _safe_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ENVIRONMENT": "local",
        "SECRET_KEY": "a-safe-random-value",
        "POSTGRES_PASSWORD": "a-safe-random-password",
        "DEBUG": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_create_production_app_raises_for_unsafe_production_settings() -> None:
    unsafe = _safe_settings(ENVIRONMENT="production", SECRET_KEY="CHANGE_ME_IN_PRODUCTION")
    with pytest.raises(ConfigurationError):
        create_production_app(app_settings=unsafe)


def test_create_production_app_serves_liveness_and_metrics() -> None:
    app = create_production_app(app_settings=_safe_settings())
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200


def test_create_production_app_omits_metrics_when_disabled() -> None:
    app = create_production_app(
        app_settings=_safe_settings(),
        ops_settings=DeploymentSettings(METRICS_ENABLED=False),
    )
    with TestClient(app) as client:
        assert client.get("/metrics").status_code == 404


def test_create_production_app_includes_readiness_route() -> None:
    app = create_production_app(app_settings=_safe_settings())
    with TestClient(app) as client:
        response = client.get("/health/ready")
    # Reachable at all (not a 404) is what matters here; a real 200/503
    # depends on live Postgres/Redis, exercised separately in test_deployment_health.py.
    assert response.status_code != 404
