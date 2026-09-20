"""Store ECG traces and GPS routes on disk, keeping only metadata in DB.

Voltage CSVs and GPX files are large, so the bytes live under the media
volume (encrypted at rest like photos) and the database keeps a small
metadata row pointing at the file.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core import crypto
from app.core.config import get_settings
from app.models.base import new_uuid
from app.services.apple_health.timeparse import to_dt

_settings = get_settings()
_TIME = re.compile(r"<time>([^<]+)</time>")
_NUM = re.compile(r"-?\d+[.,]?\d*")


def save_ecg(user_id: str, data: bytes) -> dict[str, Any]:
    """Persist an ECG CSV and return its metadata."""
    text = data.decode("utf-8", "replace")
    meta = _ecg_meta(text)
    meta["file_path"] = str(_write(user_id, "ecg", ".csv", data))
    return meta


def save_route(user_id: str, data: bytes) -> dict[str, Any]:
    """Persist a GPX route and return its metadata."""
    text = data.decode("utf-8", "replace")
    return {
        "point_count": text.count("<trkpt"),
        "started_at": _first_time(text),
        "file_path": str(_write(user_id, "routes", ".gpx", data)),
    }


def _ecg_meta(text: str) -> dict[str, Any]:
    """Best-effort parse of ECG header fields and sample count."""
    rate: float | None = None
    label: str | None = None
    when: datetime | None = None
    count = 0
    for line in text.splitlines():
        low = line.lower()
        if _is_sample(line):
            count += 1
        elif "hz" in low and rate is None:
            rate = _first_number(line)
        elif low.startswith("classification"):
            label = _field(line)
        elif ("enregistr" in low or "recorded" in low) and when is None:
            when = to_dt(_field(line))
    return _ecg_dict(rate, label, when, count)


def _ecg_dict(
    rate: float | None, label: str | None, when: datetime | None, count: int
) -> dict[str, Any]:
    """Assemble the ECG metadata mapping."""
    return {
        "sample_rate_hz": rate,
        "classification": label,
        "recorded_at": when,
        "sample_count": count,
    }


def _is_sample(line: str) -> bool:
    """Return whether a line is a single numeric voltage sample."""
    token = line.strip()
    if not token or any(char.isalpha() for char in token):
        return False
    try:
        float(token.replace(",", "."))
    except ValueError:
        return False
    return True


def _field(line: str) -> str:
    """Return the value after the first comma of a header line."""
    return line.split(",", 1)[1].strip() if "," in line else ""


def _first_number(line: str) -> float | None:
    """Return the first number found in a line, or None."""
    match = _NUM.search(line)
    return float(match.group().replace(",", ".")) if match else None


def _first_time(text: str) -> datetime | None:
    """Return the first ISO ``<time>`` in a GPX document."""
    match = _TIME.search(text)
    if match is None:
        return None
    try:
        return datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None


def _write(user_id: str, sub: str, ext: str, data: bytes) -> Path:
    """Encrypt and write bytes under the user's media directory."""
    base = Path(_settings.media_dir) / user_id / "health" / sub
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{new_uuid()}{ext}"
    path.write_bytes(crypto.encrypt(data))
    return path
