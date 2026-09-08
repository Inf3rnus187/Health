"""Default global HealthKit → metric mappings (extensible at runtime)."""

from __future__ import annotations

#: (source, external_key, metric_key). Seeded as global defaults.
DEFAULT_MAPPINGS: list[tuple[str, str, str]] = [
    ("watch", "HKQuantityTypeIdentifierBodyMass", "body.weight"),
    ("watch", "HKQuantityTypeIdentifierOxygenSaturation", "sleep.spo2_avg"),
    ("watch", "HKQuantityTypeIdentifierRestingHeartRate", "rest.hr"),
    ("watch", "HKQuantityTypeIdentifierRespiratoryRate", "sleep.resp_rate"),
    (
        "watch",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "sleep.hrv",
    ),
    (
        "watch",
        "HKQuantityTypeIdentifierAppleSleepingWristTemperature",
        "sleep.wrist_temp",
    ),
    ("watch", "HKQuantityTypeIdentifierFlightsClimbed", "stairs.floors"),
    (
        "watch",
        "HKQuantityTypeIdentifierDistanceWalkingRunning",
        "walk.distance",
    ),
    ("ppc", "AHI", "ppc.ahi"),
    ("ppc", "UsageHours", "ppc.hours_used"),
    ("ppc", "LeakMedian", "ppc.leak_median"),
    ("ppc", "PressureMedian", "ppc.pressure_median"),
]
