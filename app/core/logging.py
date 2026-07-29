"""Loguru configuration.

Replaces the standard library logging handlers with Loguru so that every
log line — ours and any third-party library that uses stdlib `logging`
(uvicorn, sqlalchemy, etc.) — ends up in the same structured, rotated sink.
"""

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.settings import settings


class InterceptHandler(logging.Handler):
    """Redirect stdlib `logging` records into Loguru.

    Without this, uvicorn/sqlalchemy logs would bypass Loguru's formatting
    and rotation and print in a different format on stdout.
    """

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Configure Loguru sinks. Call once at application startup."""
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=False,
        diagnose=settings.DEBUG,
    )

    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=settings.LOG_LEVEL,
        rotation="00:00",
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        compression="zip",
        enqueue=True,
        backtrace=False,
        diagnose=settings.DEBUG,
    )

    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation="00:00",
        retention=f"{settings.LOG_RETENTION_DAYS} days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy_logger in ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).handlers = [InterceptHandler()]
        logging.getLogger(noisy_logger).propagate = False

    logger.info("Logging configured (level={}, dir={})", settings.LOG_LEVEL, log_dir)
