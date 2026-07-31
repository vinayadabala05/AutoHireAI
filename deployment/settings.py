"""Deployment-layer settings: operational knobs, not application config.

Deliberately separate from `app.core.settings.Settings` (Sprint 1) — that
object holds *what the application needs to run* (database, security,
logging); this one holds *how the operations layer runs the process*
(readiness timeouts, whether metrics/the background worker are enabled).
Mixing the two would force every future ops knob into the same settings
object every application service also depends on. Sourced from the same
`.env` file via `pydantic_settings`, so no second secrets file to manage.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    METRICS_ENABLED: bool = True
    READINESS_TIMEOUT_SECONDS: float = 3.0
    WORKER_ENABLED: bool = False
    WORKER_POLL_INTERVAL_SECONDS: float = 300.0
    GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS: float = 30.0


@lru_cache
def get_deployment_settings() -> DeploymentSettings:
    """Cached, process-wide `DeploymentSettings` (parsed once, same convention as
    `app.core.settings.get_settings`)."""
    return DeploymentSettings()


deployment_settings = get_deployment_settings()
