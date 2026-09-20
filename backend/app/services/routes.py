"""Read one GPS route back as a downsampled list of coordinates."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.errors import NotFoundError
from app.models.health_raw import RouteFile

MAX_POINTS = 3000
_TRKPT = re.compile(r"<trkpt\b[^>]*>")
_LAT = re.compile(r'lat="(-?\d+(?:\.\d+)?)"')
_LON = re.compile(r'lon="(-?\d+(?:\.\d+)?)"')


async def track(
    session: AsyncSession, user_id: str, record_id: str
) -> list[tuple[float, float]]:
    """Return the route's ``(lat, lon)`` points, downsampled."""
    row = await session.get(RouteFile, record_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Route not found")
    raw = crypto.decrypt(Path(row.file_path).read_bytes())
    return _downsample(_extract(raw.decode("utf-8", "replace")), MAX_POINTS)


def _extract(text: str) -> list[tuple[float, float]]:
    """Pull (lat, lon) from every <trkpt>, whatever the attribute order."""
    points: list[tuple[float, float]] = []
    for tag in _TRKPT.findall(text):
        lat = _LAT.search(tag)
        lon = _LON.search(tag)
        if lat and lon:
            points.append((float(lat.group(1)), float(lon.group(1))))
    return points


def _downsample(
    points: list[tuple[float, float]], cap: int
) -> list[tuple[float, float]]:
    """Keep at most ``cap`` points by uniform decimation."""
    if len(points) <= cap:
        return points
    step = len(points) // cap
    return points[::step]
