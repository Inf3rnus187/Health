"""Default global HealthKit → metric mappings (extensible at runtime)."""

from __future__ import annotations

#: (source, external_key, metric_key). Seeded as global defaults.
DEFAULT_MAPPINGS: list[tuple[str, str, str]] = [
    ("watch", "HKQuantityTypeIdentifierBodyMass", "body.weight"),
    ("watch", "HKQuantityTypeIdentifierOxygenSaturation", "body.spo2"),
    ("watch", "HKQuantityTypeIdentifierRestingHeartRate", "rest.hr"),
    ("watch", "HKQuantityTypeIdentifierRespiratoryRate", "body.resp_rate"),
    (
        "watch",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "heart.hrv",
    ),
    (
        "watch",
        "HKQuantityTypeIdentifierAppleSleepingWristTemperature",
        "sleep.wrist_temp",
    ),
    ("watch", "HKQuantityTypeIdentifierFlightsClimbed", "activity.flights"),
    (
        "watch",
        "HKQuantityTypeIdentifierDistanceWalkingRunning",
        "activity.distance",
    ),
    ("ppc", "AHI", "ppc.ahi"),
    ("ppc", "UsageHours", "ppc.hours_used"),
    ("ppc", "LeakMedian", "ppc.leak_median"),
    ("ppc", "PressureMedian", "ppc.pressure_median"),
]
