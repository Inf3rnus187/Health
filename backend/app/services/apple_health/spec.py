"""Apple Health → metric mapping (data only).

Every HealthKit type maps to exactly one metric, under which the raw
samples are stored (``health_samples``) and a daily roll-up is cached for
dashboards (``measurements``). Unmapped types are still imported under a
synthesised ``apple.*`` key, so nothing is dropped.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class MetricSpec(NamedTuple):
    """Target metric for a HealthKit type."""

    key: str
    label: str
    domain: str
    data_type: str
    unit: str | None
    agg: str


def _q(
    hk: str,
    key: str,
    label: str,
    domain: str,
    data_type: str,
    unit: str | None,
    agg: str,
) -> tuple[str, MetricSpec]:
    """Pair a HealthKit id with its metric spec."""
    return hk, MetricSpec(key, label, domain, data_type, unit, agg)


_QUANTITY_PAIRS = (
    _q(
        "HKQuantityTypeIdentifierStepCount",
        "activity.steps",
        "Pas",
        "activity",
        "int",
        "count",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierDistanceWalkingRunning",
        "activity.distance",
        "Distance marche/course",
        "activity",
        "float",
        "km",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierDistanceCycling",
        "activity.distance_cycle",
        "Distance vélo",
        "activity",
        "float",
        "km",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierFlightsClimbed",
        "activity.flights",
        "Étages montés",
        "activity",
        "int",
        "count",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierActiveEnergyBurned",
        "activity.active_energy",
        "Énergie active",
        "activity",
        "float",
        "kcal",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierBasalEnergyBurned",
        "activity.basal_energy",
        "Énergie de repos",
        "activity",
        "float",
        "kcal",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierAppleExerciseTime",
        "activity.exercise_min",
        "Minutes d'exercice",
        "activity",
        "int",
        "min",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierAppleStandTime",
        "activity.stand_min",
        "Minutes debout",
        "activity",
        "int",
        "min",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierHeartRate",
        "heart.rate",
        "Fréquence cardiaque",
        "heart",
        "float",
        "bpm",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierRestingHeartRate",
        "rest.hr",
        "FC de repos",
        "rest",
        "int",
        "bpm",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierWalkingHeartRateAverage",
        "heart.walking_avg",
        "FC à la marche",
        "heart",
        "float",
        "bpm",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        "heart.hrv",
        "VFC (SDNN)",
        "heart",
        "float",
        "ms",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierVO2Max",
        "fitness.vo2max",
        "VO2 max",
        "fitness",
        "float",
        "ml/kg/min",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierOxygenSaturation",
        "body.spo2",
        "SpO2",
        "body",
        "float",
        "%",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierRespiratoryRate",
        "body.resp_rate",
        "Fréquence respiratoire",
        "body",
        "float",
        "resp/min",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierBodyMass",
        "body.weight",
        "Poids",
        "body",
        "float",
        "kg",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierBodyMassIndex",
        "body.bmi",
        "IMC",
        "body",
        "float",
        "count",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierBodyFatPercentage",
        "body.fat_pct",
        "Masse grasse",
        "body",
        "float",
        "%",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierLeanBodyMass",
        "body.lean_mass",
        "Masse maigre",
        "body",
        "float",
        "kg",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierWaistCircumference",
        "body.waist",
        "Tour de taille",
        "body",
        "float",
        "cm",
        "last",
    ),
    # Same field as the lab reports' glucose; the fasting-glucose marker
    # only uses lab values (a sensor reading is not a fasting value).
    _q(
        "HKQuantityTypeIdentifierBloodGlucose",
        "bio.glycemie",
        "Glycémie",
        "bio",
        "float",
        "g/L",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierHeight",
        "body.height",
        "Taille",
        "body",
        "float",
        "cm",
        "last",
    ),
    _q(
        "HKQuantityTypeIdentifierBloodPressureSystolic",
        "vitals.bp_systolic",
        "Tension systolique",
        "vitals",
        "int",
        "mmHg",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierBloodPressureDiastolic",
        "vitals.bp_diastolic",
        "Tension diastolique",
        "vitals",
        "int",
        "mmHg",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierBodyTemperature",
        "vitals.body_temp",
        "Température",
        "vitals",
        "float",
        "°C",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierAppleSleepingWristTemperature",
        "sleep.wrist_temp",
        "Température poignet",
        "sleep",
        "float",
        "°C",
        "avg",
    ),
    _q(
        "HKQuantityTypeIdentifierDietaryWater",
        "nutrition.water",
        "Eau bue",
        "nutrition",
        "float",
        "L",
        "sum",
    ),
    _q(
        "HKQuantityTypeIdentifierDietaryEnergyConsumed",
        "nutrition.energy",
        "Énergie alimentaire",
        "nutrition",
        "float",
        "kcal",
        "sum",
    ),
)

#: HealthKit quantity id → its single metric spec.
QUANTITY_SPECS: dict[str, MetricSpec] = dict(_QUANTITY_PAIRS)

SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"

#: Raw sleep-analysis samples land here (category text, no roll-up).
SLEEP_RAW = MetricSpec(
    "apple.sleep_analysis", "Analyse du sommeil", "sleep", "text", None, "last"
)

#: SleepAnalysis category value → seeded sleep metrics it adds minutes to.
#: Both the XML long form and the CSV short form (``asleepCore``) are keyed,
#: since SimpleHealthExportCSV emits the short one.
SLEEP_STAGE_MAP: dict[str, tuple[str, ...]] = {
    "HKCategoryValueSleepAnalysisAsleepDeep": ("sleep.deep", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepREM": ("sleep.rem", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepCore": ("sleep.core", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepUnspecified": ("sleep.asleep",),
    "HKCategoryValueSleepAnalysisAsleep": ("sleep.asleep",),
    "HKCategoryValueSleepAnalysisAwake": ("sleep.awake",),
    "HKCategoryValueSleepAnalysisInBed": ("sleep.time_in_bed",),
    "asleepDeep": ("sleep.deep", "sleep.asleep"),
    "asleepREM": ("sleep.rem", "sleep.asleep"),
    "asleepCore": ("sleep.core", "sleep.asleep"),
    "asleepUnspecified": ("sleep.asleep",),
    "asleep": ("sleep.asleep",),
    "awake": ("sleep.awake",),
    "inBed": ("sleep.time_in_bed",),
}

#: Roll-up metrics for workouts (summed per start day).
WORKOUT_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec("workout.count", "Séances", "workout", "int", "count", "sum"),
    MetricSpec(
        "workout.total_min", "Durée totale", "workout", "int", "min", "sum"
    ),
    MetricSpec(
        "workout.energy", "Énergie séances", "workout", "float", "kcal", "sum"
    ),
    MetricSpec(
        "workout.distance", "Distance séances", "workout", "float", "km", "sum"
    ),
)

#: Workout XML attribute → roll-up metric key.
WORKOUT_ATTR = (
    ("duration", "workout.total_min"),
    ("totalEnergyBurned", "workout.energy"),
    ("totalDistance", "workout.distance"),
)

#: Sleep-stage roll-up metrics are seeded; these keys are never recreated.
SEEDED_KEYS: frozenset[str] = frozenset(
    {
        "body.weight",
        "rest.hr",
        "sleep.wrist_temp",
        "sleep.deep",
        "sleep.rem",
        "sleep.core",
        "sleep.awake",
        "sleep.asleep",
        "sleep.time_in_bed",
    }
)


def synth_spec(hk_type: str, unit: str | None) -> MetricSpec:
    """Return a metric spec for any HealthKit type, curated or synthesised."""
    curated = QUANTITY_SPECS.get(hk_type)
    if curated is not None:
        return curated
    slug = _slug(hk_type)
    return MetricSpec(
        f"apple.{slug}", _title(slug), "apple", "float", unit, "avg"
    )


def _slug(hk_type: str) -> str:
    """Turn a HealthKit identifier into a ``snake_case`` key suffix."""
    name = re.sub(r"^HK(Quantity|Category)TypeIdentifier", "", hk_type)
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    cleaned = re.sub(r"[^a-z0-9_]", "_", snake).strip("_")
    return cleaned or "unknown"


def _title(slug: str) -> str:
    """Human label from a slug (``step_count`` → ``Step count``)."""
    return slug.replace("_", " ").capitalize()
