"""Structured (JSON) logging configuration.

Logs are emitted as JSON for easy ingestion; sensitive payloads must be
redacted by callers before logging (see §12.1).
"""

from __future__ import annotations

import logging
from typing import cast

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure ``structlog`` for JSON or console output."""
    settings = get_settings()
    logging.basicConfig(format="%(message)s", level=settings.log_level.upper())
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger named ``name``."""
    logger = structlog.get_logger(name)
    return cast(structlog.stdlib.BoundLogger, logger)
