"""Structured (JSON) logging configuration.

Logs are emitted as JSON for easy ingestion; sensitive payloads must be
redacted by callers before logging (see §12.1). The access log never
shows a token: an iPhone Shortcut sends it in the URL (``?token=…``),
which is written ``?token=***``.
"""

from __future__ import annotations

import logging
import re
from typing import cast

import structlog

from app.core.config import get_settings

_TOKEN_IN_URL = re.compile(r"([?&](?:token|access_token)=)[^&\s\"]+")
_ACCESS_LOGGERS = ("uvicorn.access", "gunicorn.access")


class _NoTokens(logging.Filter):
    """Blank the token of a URL (``?token=…``) in an access-log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Rewrite the line's message and arguments; always keep it."""
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                _redact(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def _redact(text: str) -> str:
    """``/sync/tally?token=abc&x=1`` → ``/sync/tally?token=***&x=1``."""
    return _TOKEN_IN_URL.sub(r"\1***", text)


def _hide_tokens() -> None:
    """Put the filter on the access loggers (once)."""
    for name in _ACCESS_LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, _NoTokens) for f in logger.filters):
            logger.addFilter(_NoTokens())


def configure_logging() -> None:
    """Configure ``structlog`` for JSON or console output."""
    settings = get_settings()
    logging.basicConfig(format="%(message)s", level=settings.log_level.upper())
    _hide_tokens()
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
