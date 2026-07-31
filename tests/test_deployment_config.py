"""Unit tests for `deployment.config`."""

import pytest

from app.core.settings import Settings
from deployment.config import ConfigurationError, check_configuration, validate_configuration


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ENVIRONMENT": "local",
        "SECRET_KEY": "a-safe-random-value",
        "POSTGRES_PASSWORD": "a-safe-random-password",
        "DEBUG": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_check_configuration_reports_no_problems_when_safe() -> None:
    report = check_configuration(_settings())
    assert report.is_valid is True
    assert report.problems == []


def test_check_configuration_flags_default_secret_key() -> None:
    report = check_configuration(_settings(SECRET_KEY="CHANGE_ME_IN_PRODUCTION"))
    assert report.is_valid is False
    assert any("SECRET_KEY" in problem for problem in report.problems)


def test_check_configuration_flags_default_postgres_password() -> None:
    report = check_configuration(_settings(POSTGRES_PASSWORD="autohire"))
    assert any("POSTGRES_PASSWORD" in problem for problem in report.problems)


def test_check_configuration_flags_debug_in_production() -> None:
    report = check_configuration(_settings(ENVIRONMENT="production", DEBUG=True))
    assert any("DEBUG" in problem for problem in report.problems)


def test_validate_configuration_raises_in_production_when_unsafe() -> None:
    unsafe = _settings(ENVIRONMENT="production", SECRET_KEY="CHANGE_ME_IN_PRODUCTION")
    with pytest.raises(ConfigurationError):
        validate_configuration(unsafe)


def test_validate_configuration_raises_in_staging_when_unsafe() -> None:
    unsafe = _settings(ENVIRONMENT="staging", POSTGRES_PASSWORD="autohire")
    with pytest.raises(ConfigurationError):
        validate_configuration(unsafe)


def test_validate_configuration_only_warns_in_local(caplog: pytest.LogCaptureFixture) -> None:
    unsafe = _settings(ENVIRONMENT="local", SECRET_KEY="CHANGE_ME_IN_PRODUCTION")
    validate_configuration(unsafe)  # must not raise


def test_validate_configuration_passes_when_safe() -> None:
    validate_configuration(_settings(ENVIRONMENT="production"))  # must not raise
