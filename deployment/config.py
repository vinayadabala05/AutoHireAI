"""Startup configuration validation.

Fails fast, before the process ever binds a port, if a real environment
(`staging`/`production`) is about to run with an unsafe default —
catching a forgotten `.env` override in CI/deploy rather than in a
production incident. Local/development environments only get a `logger`
warning: friction-free by default, strict where it matters.
"""

from dataclasses import dataclass, field

from loguru import logger

from app.core.settings import Settings


class ConfigurationError(Exception):
    """Raised when required configuration is missing or unsafe for the target environment."""


_UNSAFE_DEFAULTS = {
    "SECRET_KEY": "CHANGE_ME_IN_PRODUCTION",
    "POSTGRES_PASSWORD": "autohire",
}


@dataclass
class ConfigurationReport:
    environment: str
    problems: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.problems


def check_configuration(settings: Settings) -> ConfigurationReport:
    """Return every configuration problem found, without raising.

    `validate_configuration` is the fail-fast entrypoint `startup.py` calls;
    this function is the reusable, side-effect-free check it (and tests)
    build on.
    """
    problems: list[str] = []

    for field_name, unsafe_value in _UNSAFE_DEFAULTS.items():
        if getattr(settings, field_name) == unsafe_value:
            problems.append(f"{field_name} is still set to its insecure default value.")

    if settings.is_production and settings.DEBUG:
        problems.append("DEBUG must be disabled in production.")

    return ConfigurationReport(environment=settings.ENVIRONMENT, problems=problems)


def validate_configuration(settings: Settings) -> None:
    """Raise `ConfigurationError` if `settings` is unsafe for a real environment.

    Local/development environments only warn — the whole point of sensible
    defaults is that a fresh checkout runs immediately.
    """
    report = check_configuration(settings)
    if report.is_valid:
        return

    if settings.ENVIRONMENT in ("staging", "production"):
        raise ConfigurationError(
            f"Refusing to start in {settings.ENVIRONMENT!r}: " + "; ".join(report.problems)
        )

    for problem in report.problems:
        logger.bind(environment=settings.ENVIRONMENT).warning("Configuration warning: {}", problem)
