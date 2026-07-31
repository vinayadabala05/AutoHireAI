"""Graceful startup: validate configuration, configure logging, assemble the app.

`create_production_app()` is the production ASGI entrypoint
(`uvicorn deployment.startup:app`), distinct from `app.main:app` (Sprint
1's dev/test entrypoint). It reuses Sprint 1's own building blocks —
`api_router`, `register_exception_handlers`, and `lifespan` itself — so
routing, exception handling, and DB-engine disposal behave identically to
`app.main`; this module only *adds* config validation, production
logging, readiness, and metrics on top, exactly what a deployment layer
should be additive over, never a fork of, application logic.
"""

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.settings import Settings, settings
from app.main import lifespan as base_lifespan
from deployment.config import validate_configuration
from deployment.health import build_readiness_router
from deployment.logging import configure_production_logging
from deployment.metrics import MetricsMiddleware, MetricsRegistry, build_metrics_router
from deployment.settings import DeploymentSettings, deployment_settings
from deployment.shutdown import StoppableWorker, build_production_lifespan


def create_production_app(
    app_settings: Settings = settings,
    ops_settings: DeploymentSettings = deployment_settings,
    worker: StoppableWorker | None = None,
) -> FastAPI:
    """Validate configuration, configure logging, and assemble the production app.

    Raises `deployment.config.ConfigurationError` immediately if
    `app_settings` is unsafe for `app_settings.ENVIRONMENT` — before the
    process ever binds a port, and before any route can be hit.
    """
    validate_configuration(app_settings)
    configure_production_logging(app_settings)
    logger.info("Assembling production application for {}.", app_settings.ENVIRONMENT)

    application = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        debug=app_settings.DEBUG,
    )
    register_exception_handlers(application)
    application.include_router(api_router)
    application.include_router(
        build_readiness_router(app_settings, ops_settings.READINESS_TIMEOUT_SECONDS)
    )

    if ops_settings.METRICS_ENABLED:
        registry = MetricsRegistry()
        application.add_middleware(MetricsMiddleware, registry=registry)
        application.include_router(build_metrics_router(registry))

    application.router.lifespan_context = build_production_lifespan(
        base_lifespan, ops_settings, worker
    )
    return application


app = create_production_app()
