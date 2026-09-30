"""Samples written in bulk (COPY on PostgreSQL): defaults, counts kept."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models.health_raw import HealthSample
from app.models.sample_counts import REFILL
from app.models.user import User
from app.services import sample_counts, sample_writes
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import QUANTITY_SPECS
from sqlalchemy import select, text


async def _admin() -> str:
    async with SessionFactory() as session:
        email = get_settings().admin_email
        user = await session.execute(select(User).where(User.email == email))
        return user.scalar_one().id


def test_a_missing_column_gets_its_default() -> None:
    record = dict(
        zip(
            sample_writes._NAMES,
            sample_writes._record({"user_id": "u", "metric_id": "m"}),
            strict=True,
        )
    )
    assert record["source"] == "apple"
    assert len(record["id"]) == 36
    assert record["created_at"].tzinfo is not None
    assert record["value_num"] is None


async def test_written_samples_are_stored_and_counted() -> None:
    """The rows land as given; the counts equal a count from scratch."""
    user_id = await _admin()
    start = datetime(2025, 2, 1, 8, 0, tzinfo=UTC)
    spec = QUANTITY_SPECS["HKQuantityTypeIdentifierHeartRate"]
    async with SessionFactory() as session:
        metric_id = await MetricCache().id_for(session, spec)
        rows = [
            {
                "user_id": user_id,
                "metric_id": metric_id,
                "start_at": start + timedelta(minutes=i),
                "value_num": 60.5 + i,
                "unit": "count/min",
                "source": "healthkit",
                "external_id": f"ecrit-{i}",
            }
            for i in range(1200)
        ]
        await sample_writes.write(session, rows)
        await session.commit()
        stored = await session.execute(
            select(HealthSample.value_num)
            .where(HealthSample.external_id.like("ecrit-%"))
            .order_by(HealthSample.start_at)
        )
        assert list(stored.scalars()) == [60.5 + i for i in range(1200)]
        kept = sorted(await sample_counts.of_user(session, user_id))
        await session.execute(text("DELETE FROM sample_counts"))
        await session.execute(text(REFILL.format(where="")))
        assert sorted(await sample_counts.of_user(session, user_id)) == kept
        await session.rollback()
