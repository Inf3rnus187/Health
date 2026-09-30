"""The page's timings and limits come from the environment, not the code."""

from __future__ import annotations

import pytest
from app.core.tuning import Tuning
from app.services import spending, work_legal
from httpx import AsyncClient

SETTINGS = "/api/v1/system/settings"


async def test_the_page_reads_its_settings_before_signing_in(
    client: AsyncClient,
) -> None:
    got = await client.get(SETTINGS)
    assert got.status_code == 200
    body = got.json()
    assert body["retry_s"] == 5 and body["poll_s"] == 5
    assert body["renew_every_s"] == 15 * 60 - 180  # token life less margin
    assert body["page_sizes"] == [10, 25, 50, 100, 200]
    assert body["photo_refresh_s"] == [1.5, 4, 8, 13]
    assert body["meal_photos"] == 7
    assert body["work_max_week_hours"] == 48


async def test_every_account_sees_the_same_and_nothing_of_a_user(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    mine = (await client.get(SETTINGS, headers=auth)).json()
    theirs = (await client.get(SETTINGS, headers=member)).json()
    assert mine == theirs
    assert "example.com" not in str(mine)


def test_lists_and_rules_are_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEB_PAGE_SIZES", "5,20")
    monkeypatch.setenv("WEB_PHOTO_REFRESH_S", "2,5.5")
    monkeypatch.setenv("WORK_MAX_WEEK_HOURS", "46")
    monkeypatch.setenv("WORK_NIGHT_START", "22:30")
    tuned = Tuning()
    assert tuned.web_page_sizes == [5, 20]
    assert tuned.web_photo_refresh_s == [2, 5.5]
    assert tuned.work_max_week_hours == 46
    assert tuned.work_night_start == "22:30"


def test_a_wrong_night_hour_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORK_NIGHT_START", "9pm")
    with pytest.raises(ValueError):
        Tuning()


def test_reports_write_the_rules_in_force() -> None:
    assert work_legal.NIGHT_FROM == "21 h"
    assert work_legal.NIGHT_TEXT == "21 h - 6 h"


def test_a_late_window_may_stay_before_midnight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert spending._late(23) and spending._late(4) and not spending._late(12)
    monkeypatch.setattr(spending, "LATE_FROM", 19)
    monkeypatch.setattr(spending, "LATE_UNTIL", 23)
    assert spending._late(20) and not spending._late(23)
    assert not spending._late(2)
