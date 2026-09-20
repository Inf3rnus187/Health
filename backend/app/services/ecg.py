"""Read one ECG trace back as a downsampled voltage series."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.errors import NotFoundError
from app.models.health_raw import EcgRecord

MAX_POINTS = 5000


async def series(
    session: AsyncSession, user_id: str, record_id: str
) -> tuple[float | None, list[float]]:
    """Return (sample rate, downsampled voltages) for one ECG."""
    row = await session.get(EcgRecord, record_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("ECG not found")
    raw = crypto.decrypt(Path(row.file_path).read_bytes())
    values = _voltages(raw.decode("utf-8", "replace"))
    return row.sample_rate_hz, _downsample(values, MAX_POINTS)


def _voltages(text: str) -> list[float]:
    """Collect the numeric voltage lines from an ECG CSV."""
    out: list[float] = []
    for line in text.splitlines():
        token = line.strip()
        if not token or any(char.isalpha() for char in token):
            continue
        try:
            out.append(float(token.replace(",", ".")))
        except ValueError:
            continue
    return out


def _downsample(values: list[float], cap: int) -> list[float]:
    """Keep at most ``cap`` points by uniform decimation."""
    if len(values) <= cap:
        return values
    step = len(values) // cap
    return values[::step]
