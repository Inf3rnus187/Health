"""Per-day accumulator and the rule that turns it into one daily value."""

from __future__ import annotations

from datetime import UTC, datetime

#: The channels carrying the same HealthKit data (one is taken a day):
#: the native export, Health Auto Export and the iPhone app.
HEALTHKIT = frozenset({"apple", "auto-export", "healthkit"})


class Acc:
    """Running count / sum / min / max / latest of one source's day."""

    __slots__ = ("count", "high", "last", "last_at", "low", "total")

    def __init__(self) -> None:
        """Start empty."""
        self.count = 0
        self.total = 0.0
        self.low = float("inf")
        self.high = float("-inf")
        self.last = 0.0
        self.last_at: datetime | None = None

    def add(self, at: datetime, value: float) -> None:
        """Fold in one sample."""
        self.count += 1
        self.total += value
        self.low = min(self.low, value)
        self.high = max(self.high, value)
        if self.last_at is None or at >= self.last_at:
            self.last, self.last_at = value, at

    def merge(self, other: Acc) -> None:
        """Fold in another accumulator."""
        self.count += other.count
        self.total += other.total
        self.low = min(self.low, other.low)
        self.high = max(self.high, other.high)
        if other.last_at is not None and (
            self.last_at is None or other.last_at >= self.last_at
        ):
            self.last, self.last_at = other.last, other.last_at


def reduce_day(
    sources: dict[str, Acc], agg: str
) -> tuple[float, str, datetime]:
    """One HealthKit channel (most samples) + other sources → a value."""
    healthkit = {s: a for s, a in sources.items() if s in HEALTHKIT}
    others = {s: a for s, a in sources.items() if s not in HEALTHKIT}
    chosen = dict(others)
    if healthkit:
        best = max(healthkit, key=lambda s: healthkit[s].count)
        chosen[best] = healthkit[best]
    total = Acc()
    for acc in chosen.values():
        total.merge(acc)
    label = max(chosen, key=lambda s: chosen[s].count)
    return _value(total, agg), label, total.last_at or datetime.now(UTC)


def _value(acc: Acc, agg: str) -> float:
    """Apply the metric's aggregation."""
    if agg == "sum":
        return acc.total
    if agg == "min":
        return acc.low
    if agg == "max":
        return acc.high
    if agg == "last":
        return acc.last
    return acc.total / acc.count
