"""Top-level API router.

Aggregates all versioned sub-routers into one object that `main.py` mounts.
New feature routers (jobs, resumes, applications, ...) get added here as
they're built — call sites elsewhere never need to change.
"""

from fastapi import APIRouter

from app.api import health

api_router = APIRouter()
api_router.include_router(health.router)
