"""The API's access log: its time, its duration, never a token."""

from __future__ import annotations

import logging
import re

from app.core.access_log import LOGGER
from app.core.logging import configure_logging
from httpx import AsyncClient


class _Keep(logging.Handler):
    """Keep the formatted lines."""

    def __init__(self, formatter: logging.Formatter | None) -> None:
        super().__init__()
        self.lines: list[str] = []
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


async def test_each_request_has_its_time_and_duration_never_a_token(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    configure_logging()
    configure_logging()  # twice: still one handler
    access = logging.getLogger(LOGGER)
    assert len(access.handlers) == 1
    assert logging.getLogger("uvicorn.access").disabled  # no duplicate line
    keep = _Keep(access.handlers[0].formatter)
    access.addHandler(keep)
    try:
        await client.post(
            "/api/v1/sync/tally?token=phx_secret.abc&x=1",
            json={"metric": "habit.coffee"},
        )
        await client.get("/api/v1/summary", headers=auth)
    finally:
        access.removeHandler(keep)
    tally, summary = keep.lines
    assert "phx_secret" not in tally
    assert "/api/v1/sync/tally?token=***&x=1" in tally
    stamp = r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \+0000 "
    assert re.match(
        stamp + r'.* "GET /api/v1/summary HTTP/1\.1" 200 \d+ ms', summary
    )
