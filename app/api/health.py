"""Liveness/readiness endpoint.

Kept dependency-free by design (no DB/Redis check on the plain `/health`
route) so orchestrators (Docker, k8s) can use it as a cheap liveness probe
that only fails if the process itself is unresponsive.
"""

from fastapi import APIRouter

from app.core.constants import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": HealthStatus.OK.value}
