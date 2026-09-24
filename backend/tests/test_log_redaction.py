"""An API token sent in a URL (iPhone Shortcut) never reaches the logs."""

from __future__ import annotations

import logging

import pytest
from app.core.logging import configure_logging


def test_the_access_log_hides_a_token_in_the_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_logging()
    configure_logging()  # twice: still one filter
    access = logging.getLogger("uvicorn.access")
    assert len(access.filters) == 1
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        access.info(
            '%s - "%s %s HTTP/%s" %d',
            "10.0.0.2:5123",
            "POST",
            "/api/v1/sync/tally?token=phx_secret.abc&x=1",
            "1.1",
            200,
        )
    assert "phx_secret" not in caplog.text
    assert "/api/v1/sync/tally?token=***&x=1" in caplog.text
