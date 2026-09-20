"""Apple Health export → metric mapping (data only).

Declares which HealthKit identifiers feed which metric keys, and the
metric rows the importer ensures exist. Aggregation and canonical unit
are read back from ``METRIC_DEFS`` so every fact has a single source of
truth.
"""

from __future__ import annotations

from typing import NamedTuple


class MetricDef(NamedTuple):
    """A metric the importer targets (created when still missing)."""

    key: str
    label: str
    domain: str
    data_type: str
    unit: str | None
    agg: str


def _d(
    key: str,
    label: str,
    domain: str,
    data_type: str,
    unit: str | None,
    agg: str,
) -> MetricDef:
    """Terse constructor keeping the table below readable."""
    return MetricDef(key, label, domain, data_type, unit, agg)


#: Every metric an Apple Health import can write to. New keys are created
#: on import; keys already seeded (e.g. ``body.weight``) are left as-is.
METRIC_DEFS: tuple[MetricDef, ...] = (
    _d("activity.steps", "Pas", "activity", "int", "count", "sum"),
    _d("activity.distance", "Distance", "activity", "float", "km", "sum"),
    _d("activity.flights", "Étages", "activity", "int", "count", "sum"),
    _d(
        "activity.active_energy",
        "Énergie active",
        "activity",
        "float",
        "kcal",
        "sum",
    ),
    _d(
        "activity.exercise_min",
        "Minutes d'exercice",
        "activity",
        "int",
        "min",
        "sum",
    ),
    _d("activity.stand_min", "Minutes debout", "activity", "int", "min", "sum"),
    _d(
        "activity.distance_cycle",
        "Distance vélo",
        "activity",
        "float",
        "km",
        "sum",
    ),
    _d("heart.rate_avg", "FC moyenne", "heart", "float", "bpm", "avg"),
    _d("heart.rate_min", "FC minimale", "heart", "float", "bpm", "min"),
    _d("heart.rate_max", "FC maximale", "heart", "float", "bpm", "max"),
    _d("heart.hrv", "VFC (SDNN)", "heart", "float", "ms", "avg"),
    _d("heart.walking_avg", "FC à la marche", "heart", "float", "bpm", "avg"),
    _d("fitness.vo2max", "VO2 max", "fitness", "float", "ml/kg/min", "last"),
    _d("body.spo2_avg", "SpO2 moyenne", "body", "float", "%", "avg"),
    _d("body.spo2_min", "SpO2 minimale", "body", "float", "%", "min"),
    _d(
        "body.resp_rate",
        "Fréquence respiratoire",
        "body",
        "float",
        "resp/min",
        "avg",
    ),
    _d("body.bmi", "IMC", "body", "float", "count", "last"),
    _d("body.fat_pct", "Masse grasse", "body", "float", "%", "last"),
    _d("body.lean_mass", "Masse maigre", "body", "float", "kg", "last"),
    _d("body.height", "Taille", "body", "float", "cm", "last"),
    _d(
        "vitals.bp_systolic",
        "Tension systolique",
        "vitals",
        "int",
        "mmHg",
        "avg",
    ),
    _d(
        "vitals.bp_diastolic",
        "Tension diastolique",
        "vitals",
        "int",
        "mmHg",
        "avg",
    ),
    _d("vitals.body_temp", "Température", "vitals", "float", "°C", "avg"),
    _d("nutrition.water", "Eau bue", "nutrition", "float", "L", "sum"),
    _d(
        "nutrition.energy",
        "Énergie alimentaire",
        "nutrition",
        "float",
        "kcal",
        "sum",
    ),
    _d("workout.count", "Séances", "workout", "int", "count", "sum"),
    _d(
        "workout.total_min",
        "Durée d'entraînement",
        "workout",
        "int",
        "min",
        "sum",
    ),
    _d("workout.energy", "Énergie séances", "workout", "float", "kcal", "sum"),
    _d("workout.distance", "Distance séances", "workout", "float", "km", "sum"),
    # Keys already in the seed catalogue, listed so aggregation and unit
    # lookups resolve; the importer never recreates them (see SEEDED_KEYS).
    _d("body.weight", "Poids", "body", "float", "kg", "last"),
    _d("rest.hr", "FC de repos", "rest", "int", "bpm", "avg"),
    _d(
        "sleep.wrist_temp", "Température poignet", "sleep", "float", "°C", "avg"
    ),
    _d("sleep.deep", "Sommeil profond", "sleep", "duration", "min", "sum"),
    _d("sleep.rem", "Sommeil REM", "sleep", "duration", "min", "sum"),
    _d("sleep.core", "Sommeil léger", "sleep", "duration", "min", "sum"),
    _d("sleep.awake", "Éveillé", "sleep", "duration", "min", "sum"),
    _d("sleep.asleep", "Endormi", "sleep", "duration", "min", "sum"),
    _d("sleep.time_in_bed", "Temps au lit", "sleep", "duration", "min", "sum"),
)

#: Keys already provided by the seed catalogue; never recreated.
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

#: HealthKit quantity identifier → metric keys it feeds.
QUANTITY_MAP: dict[str, tuple[str, ...]] = {
    "HKQuantityTypeIdentifierStepCount": ("activity.steps",),
    "HKQuantityTypeIdentifierDistanceWalkingRunning": ("activity.distance",),
    "HKQuantityTypeIdentifierFlightsClimbed": ("activity.flights",),
    "HKQuantityTypeIdentifierActiveEnergyBurned": ("activity.active_energy",),
    "HKQuantityTypeIdentifierAppleExerciseTime": ("activity.exercise_min",),
    "HKQuantityTypeIdentifierAppleStandTime": ("activity.stand_min",),
    "HKQuantityTypeIdentifierDistanceCycling": ("activity.distance_cycle",),
    "HKQuantityTypeIdentifierHeartRate": (
        "heart.rate_avg",
        "heart.rate_min",
        "heart.rate_max",
    ),
    "HKQuantityTypeIdentifierRestingHeartRate": ("rest.hr",),
    "HKQuantityTypeIdentifierWalkingHeartRateAverage": ("heart.walking_avg",),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("heart.hrv",),
    "HKQuantityTypeIdentifierVO2Max": ("fitness.vo2max",),
    "HKQuantityTypeIdentifierOxygenSaturation": (
        "body.spo2_avg",
        "body.spo2_min",
    ),
    "HKQuantityTypeIdentifierRespiratoryRate": ("body.resp_rate",),
    "HKQuantityTypeIdentifierBodyMass": ("body.weight",),
    "HKQuantityTypeIdentifierBodyMassIndex": ("body.bmi",),
    "HKQuantityTypeIdentifierBodyFatPercentage": ("body.fat_pct",),
    "HKQuantityTypeIdentifierLeanBodyMass": ("body.lean_mass",),
    "HKQuantityTypeIdentifierHeight": ("body.height",),
    "HKQuantityTypeIdentifierBloodPressureSystolic": ("vitals.bp_systolic",),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": ("vitals.bp_diastolic",),
    "HKQuantityTypeIdentifierBodyTemperature": ("vitals.body_temp",),
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": (
        "sleep.wrist_temp",
    ),
    "HKQuantityTypeIdentifierDietaryWater": ("nutrition.water",),
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": ("nutrition.energy",),
}

#: SleepAnalysis category value → sleep metrics it adds minutes to.
SLEEP_MAP: dict[str, tuple[str, ...]] = {
    "HKCategoryValueSleepAnalysisAsleepDeep": ("sleep.deep", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepREM": ("sleep.rem", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepCore": ("sleep.core", "sleep.asleep"),
    "HKCategoryValueSleepAnalysisAsleepUnspecified": ("sleep.asleep",),
    "HKCategoryValueSleepAnalysisAsleep": ("sleep.asleep",),
    "HKCategoryValueSleepAnalysisAwake": ("sleep.awake",),
    "HKCategoryValueSleepAnalysisInBed": ("sleep.time_in_bed",),
}

#: Workout attribute → metric key it feeds (summed per start day).
WORKOUT_MAP: tuple[tuple[str, str], ...] = (
    ("duration", "workout.total_min"),
    ("totalEnergyBurned", "workout.energy"),
    ("totalDistance", "workout.distance"),
)

SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"

#: Daily aggregation and canonical unit per metric key.
AGG_BY_KEY: dict[str, str] = {d.key: d.agg for d in METRIC_DEFS}
CANON_UNIT: dict[str, str | None] = {d.key: d.unit for d in METRIC_DEFS}
