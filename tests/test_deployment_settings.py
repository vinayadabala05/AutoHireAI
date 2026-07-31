"""Unit tests for `deployment.settings.DeploymentSettings`."""

from deployment.settings import DeploymentSettings, get_deployment_settings


def test_defaults_are_sensible() -> None:
    ops_settings = DeploymentSettings()
    assert ops_settings.METRICS_ENABLED is True
    assert ops_settings.WORKER_ENABLED is False
    assert ops_settings.READINESS_TIMEOUT_SECONDS > 0
    assert ops_settings.GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS > 0


def test_overrides_are_respected() -> None:
    ops_settings = DeploymentSettings(METRICS_ENABLED=False, WORKER_POLL_INTERVAL_SECONDS=60.0)
    assert ops_settings.METRICS_ENABLED is False
    assert ops_settings.WORKER_POLL_INTERVAL_SECONDS == 60.0


def test_get_deployment_settings_is_cached() -> None:
    assert get_deployment_settings() is get_deployment_settings()
