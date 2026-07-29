"""Project-wide constants and enums.

Values here are true constants (not environment-dependent config — those
belong in `settings.py`). Centralizing them avoids magic strings/numbers
scattered across services, repositories, and schemas.
"""

from enum import StrEnum


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


API_V1_STR = "/api/v1"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
REQUEST_ID_HEADER = "X-Request-ID"
