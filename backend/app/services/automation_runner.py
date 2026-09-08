"""Execute an automation's action (capture / reminder, §7.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import Automation
from app.schemas.capture import CaptureRequest
from app.services import capture

_CAPTURE_KEYS = {"date_key", "weight", "photo_face", "photo_profil"}


def _capture_request(action: dict[str, Any]) -> CaptureRequest:
    """Build a CaptureRequest from an automation's action payload."""
    raw = action.get("capture", {})
    kwargs = {k: v for k, v in raw.items() if k in _CAPTURE_KEYS}
    return CaptureRequest(**kwargs)


async def run(
    session: AsyncSession,
    user_id: str,
    automation: Automation,
    *,
    source: str,
    token_id: str | None = None,
) -> dict[str, Any]:
    """Run the automation's action and return a small result summary."""
    action = automation.action or {}
    kind = action.get("type", "noop")
    if kind == "capture":
        result = await capture.capture(
            session,
            user_id,
            _capture_request(action),
            source=source,
            token_id=token_id,
        )
        return {"type": "capture", "event_id": result.event_id}
    if kind == "reminder":
        return {"type": "reminder", "message": action.get("message", "")}
    return {"type": kind, "status": "noop"}
