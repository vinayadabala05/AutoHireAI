"""Production logging: adds a machine-parsable JSON sink on top of Sprint 1's setup.

`app.core.logging.configure_logging()` (Sprint 1) already gives every
environment colorized stdout plus rotated file sinks — exactly what local
development wants. A real deployment behind a log aggregator (ELK,
Datadog, CloudWatch) wants one line of structured JSON per record instead;
this module calls Sprint 1's `configure_logging()` first (reused, not
duplicated) and, only in `staging`/`production`, adds one more `loguru`
sink with `serialize=True`.
"""

import sys

from loguru import logger

from app.core.logging import configure_logging
from app.core.settings import Settings


def configure_production_logging(settings: Settings) -> None:
    """Configure logging for `settings.ENVIRONMENT`.

    Always reuses Sprint 1's `configure_logging()` first; adds a JSON stdout
    sink on top of it only for `staging`/`production`, where a log
    aggregator — not a human terminal — is the real reader.
    """
    configure_logging()

    if settings.ENVIRONMENT in ("staging", "production"):
        logger.add(sys.stdout, level=settings.LOG_LEVEL, serialize=True, backtrace=False)
        logger.info("Structured JSON logging enabled for {}.", settings.ENVIRONMENT)
