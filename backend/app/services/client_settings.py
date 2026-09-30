"""What the web page needs to know of the hub's settings.

Its timings (retries, polls, refreshes) and the limits its forms show,
all from the environment (app/core/tuning.py): nothing secret, nothing
of a user's.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings

_TIMINGS = (
    "retry_s",
    "refresh_timeout_s",
    "update_check_s",
    "update_look_s",
    "update_state_s",
    "update_recent_s",
    "poll_s",
    "reconcile_refresh_s",
    "reconcile_refresh_steps",
    "reanalysis_refresh_s",
    "reanalysis_refresh_steps",
    "photo_refresh_s",
    "reload_guard_s",
    "page_sizes",
)
#: A session is never renewed more often than this (seconds).
_RENEW_FLOOR_S = 30


def client_settings() -> dict[str, Any]:
    """The page's timings (seconds) and its forms' limits."""
    s = get_settings()
    found: dict[str, Any] = {k: getattr(s, f"web_{k}") for k in _TIMINGS}
    ttl = s.access_token_ttl_min * 60
    found["renew_every_s"] = max(_RENEW_FLOOR_S, ttl - s.web_renew_margin_s)
    found["page_sizes"] = [int(n) for n in s.web_page_sizes]
    found["meal_photos"] = s.meal_max_photos + 1
    found["meal_analysis_max_delay_min"] = s.meal_analysis_max_delay_min
    found["work_max_week_hours"] = s.work_max_week_hours
    return found
