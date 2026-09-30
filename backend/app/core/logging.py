"""Structured (JSON) logging configuration.

Logs are emitted as JSON for easy ingestion; sensitive payloads must be
redacted by callers before logging (see §12.1). The access log never
shows a token: an iPhone Shortcut sends it in the URL (``?token=…``),
which is written ``?token=***``.
"""

from __future__ import annotations

import logging
import re
import time
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
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def redact(text: str) -> str:
    """``/sync/tally?token=abc&x=1`` → ``/sync/tally?token=***&x=1``."""
    return _TOKEN_IN_URL.sub(r"\1***", text)


def _hide_tokens() -> None:
    """Put the filter on the access loggers (once)."""
    for name in _ACCESS_LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, _NoTokens) for f in logger.filters):
            logger.addFilter(_NoTokens())


#: The time of a log line, in UTC like nginx's (« 2026-09-30 05:37:56 +0000 »).
_TIME = "%Y-%m-%d %H:%M:%S +0000"


def _stamped(fmt: str) -> logging.Formatter:
    """A formatter starting with the UTC time."""
    formatter = logging.Formatter(f"%(asctime)s {fmt}", _TIME)
    formatter.converter = time.gmtime
    return formatter


def _access_lines() -> None:
    """The API's access lines (with time and duration), not uvicorn's."""
    from app.core.access_log import LOGGER

    access = logging.getLogger(LOGGER)
    if not access.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_stamped("%(message)s"))
        access.addHandler(handler)
        access.setLevel(logging.INFO)
        access.propagate = False
    logging.getLogger("uvicorn.access").disabled = True


def configure_logging() -> None:
    """Configure ``structlog`` for JSON or console output."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    for handler in logging.getLogger().handlers:
        handler.setFormatter(_stamped("%(levelname)s %(name)s %(message)s"))
    _hide_tokens()
    _access_lines()
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
