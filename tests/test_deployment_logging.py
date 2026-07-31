"""Unit tests for `deployment.logging`."""

from app.core.settings import Settings
from deployment.logging import configure_production_logging


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"ENVIRONMENT": "local"}
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_configure_production_logging_keeps_sprint1_sink_count_for_local() -> None:
    from loguru import logger

    configure_production_logging(_settings(ENVIRONMENT="local"))
    # Sprint 1's configure_logging() always installs exactly 3 sinks
    # (stdout, app file, error file); local/development add nothing on top.
    assert len(logger._core.handlers) == 3  # noqa: SLF001


def test_configure_production_logging_adds_one_json_sink_for_production() -> None:
    from loguru import logger

    configure_production_logging(_settings(ENVIRONMENT="production"))
    assert len(logger._core.handlers) == 4  # noqa: SLF001
