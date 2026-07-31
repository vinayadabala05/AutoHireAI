"""Readiness checks: is the process ready to serve traffic, not just alive.

Complements Sprint 1's `/health` (a dependency-free liveness probe by
design — see `app/api/health.py`) with a readiness check that verifies
the two services `docker-compose.yml` provisions the app to depend on:
Postgres (reusing `app.database.database.check_database_connection`,
Sprint 1) and Redis. Neither dependency's check function existed for
Redis before this sprint, so it's added here rather than inside Sprint
1's `app/database/` package, keeping this sprint additive.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
from redis.asyncio import Redis

from app.core.constants import HealthStatus
from app.core.settings import Settings
from app.database.database import check_database_connection


@dataclass
class ReadinessReport:
    status: HealthStatus
    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.status is HealthStatus.OK


async def check_redis_connection(settings: Settings, timeout_seconds: float) -> bool:
    client: Redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=timeout_seconds)
    try:
        return bool(await asyncio.wait_for(client.ping(), timeout=timeout_seconds))
    except Exception as exc:
        logger.warning("Redis readiness check failed: {}", exc)
        return False
    finally:
        await client.aclose()


async def _guarded(check: Callable[[], Awaitable[bool]], timeout_seconds: float) -> bool:
    try:
        return bool(await asyncio.wait_for(check(), timeout=timeout_seconds))
    except Exception as exc:
        logger.warning("Readiness check raised: {}", exc)
        return False


async def build_readiness_report(
    settings: Settings, timeout_seconds: float = 3.0
) -> ReadinessReport:
    """Run every dependency check concurrently and summarize the result."""
    database_ok, redis_ok = await asyncio.gather(
        _guarded(check_database_connection, timeout_seconds),
        _guarded(lambda: check_redis_connection(settings, timeout_seconds), timeout_seconds),
    )
    checks = {"database": database_ok, "redis": redis_ok}
    status = HealthStatus.OK if all(checks.values()) else HealthStatus.DOWN
    return ReadinessReport(status=status, checks=checks)


def build_readiness_router(settings: Settings, timeout_seconds: float = 3.0) -> APIRouter:
    """Build a fresh `/health/ready` `APIRouter` bound to `settings`/`timeout_seconds`.

    Returns a new router per call (rather than mutating a shared module-level
    one) so `startup.py` — and tests — can call this repeatedly without
    accumulating duplicate routes.
    """
    router = APIRouter(tags=["health"])

    @router.get("/health/ready")
    async def readiness() -> JSONResponse:
        report = await build_readiness_report(settings, timeout_seconds)
        body = {"status": report.status.value, "checks": report.checks}
        return JSONResponse(content=body, status_code=200 if report.is_ready else 503)

    return router
