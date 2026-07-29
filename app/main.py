"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

The app factory pattern (`create_app`) keeps this importable and
side-effect-free for testing (pytest imports `app` without starting a
server), while still exposing a module-level `app` object for uvicorn/gunicorn.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.settings import settings
from app.database.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    logger.info("Starting {} ({})", settings.APP_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down {}", settings.APP_NAME)
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
