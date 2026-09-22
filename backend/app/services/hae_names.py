"""Health Auto Export metric names → HealthKit identifiers (data file).

Sources: the app's official server enum, its TCP-server filter list and
real 2022-2026 payloads. The app renamed several metrics over time, so
every spelling seen maps to the same identifier — i.e. the same metric
key a native Apple export creates. Long lines are allowed here.
"""

from __future__ import annotations

_Q = "HKQuantityTypeIdentifier"
_C = "HKCategoryTypeIdentifier"

# fmt: off
_QUANTITY_NAMES: dict[str, str] = {
    # Activité
    "step_count": "StepCount",
    "walking_running_distance": "DistanceWalkingRunning", "walk_run_distance": "DistanceWalkingRunning", "distance_walking_running": "DistanceWalkingRunning",
    "cycling_distance": "DistanceCycling", "swimming_distance": "DistanceSwimming", "wheelchair_distance": "DistanceWheelchair",
    "distance_downhill_snow_sports": "DistanceDownhillSnowSports", "downhill_snow_sports": "DistanceDownhillSnowSports",
    "flights_climbed": "FlightsClimbed",
    "push_count": "PushCount", "wheelchair_push_count": "PushCount",
    "swimming_stroke_count": "SwimmingStrokeCount", "swim_stroke_count": "SwimmingStrokeCount",
    "active_energy": "ActiveEnergyBurned", "basal_energy_burned": "BasalEnergyBurned", "basal_energy": "BasalEnergyBurned",
    "apple_exercise_time": "AppleExerciseTime", "apple_move_time": "AppleMoveTime",
    "apple_stand_time": "AppleStandTime", "apple_standtime": "AppleStandTime",
    "physical_effort": "PhysicalEffort", "time_in_daylight": "TimeInDaylight",
    "running_speed": "RunningSpeed", "running_power": "RunningPower", "running_stride_length": "RunningStrideLength",
    "running_vertical_oscillation": "RunningVerticalOscillation", "running_ground_contact_time": "RunningGroundContactTime",
    "cycling_speed": "CyclingSpeed", "cycling_power": "CyclingPower", "cycling_cadence": "CyclingCadence",
    "cycling_functional_threshold_power": "CyclingFunctionalThresholdPower",
    # Corps
    "weight_body_mass": "BodyMass", "body_mass": "BodyMass", "height": "Height",
    "body_mass_index": "BodyMassIndex", "body_fat_percentage": "BodyFatPercentage",
    "lean_body_mass": "LeanBodyMass", "waist_circumference": "WaistCircumference",
    "apple_sleeping_wrist_temperature": "AppleSleepingWristTemperature",
    # Cœur
    "heart_rate": "HeartRate", "resting_heart_rate": "RestingHeartRate",
    "walking_heart_rate_average": "WalkingHeartRateAverage", "walking_heart_rate": "WalkingHeartRateAverage",
    "heart_rate_variability": "HeartRateVariabilitySDNN",
    "cardio_recovery": "HeartRateRecoveryOneMinute", "heart_rate_recovery_one_minute": "HeartRateRecoveryOneMinute",
    "vo2_max": "VO2Max", "vo2max": "VO2Max",
    "atrial_fibrillation_burden": "AtrialFibrillationBurden",
    # Mobilité
    "walking_speed": "WalkingSpeed", "walking_step_length": "WalkingStepLength",
    "walking_asymmetry_percentage": "WalkingAsymmetryPercentage",
    "walking_double_support_percentage": "WalkingDoubleSupportPercentage",
    "stair_speed_up": "StairAscentSpeed", "stair_speed_down": "StairDescentSpeed",
    "six_minute_walking_test_distance": "SixMinuteWalkTestDistance",
    # Respiration / signes vitaux
    "respiratory_rate": "RespiratoryRate",
    "blood_oxygen_saturation": "OxygenSaturation", "oxygen_saturation": "OxygenSaturation",
    "breathing_disturbances": "AppleSleepingBreathingDisturbances",
    "forced_vital_capacity": "ForcedVitalCapacity",
    "forced_expiratory_volume_1": "ForcedExpiratoryVolume1", "forced_expiratory_volume": "ForcedExpiratoryVolume1",
    "peak_expiratory_flow_rate": "PeakExpiratoryFlowRate", "inhaler_usage": "InhalerUsage",
    "peripheral_perfusion_index": "PeripheralPerfusionIndex",
    "blood_glucose": "BloodGlucose", "body_temperature": "BodyTemperature",
    "basal_body_temperature": "BasalBodyTemperature", "insulin_delivery": "InsulinDelivery",
    "blood_alcohol_content": "BloodAlcoholContent",
    # Autres
    "environmental_audio_exposure": "EnvironmentalAudioExposure", "environmental_audio": "EnvironmentalAudioExposure",
    "headphone_audio_exposure": "HeadphoneAudioExposure", "headphone_audio": "HeadphoneAudioExposure",
    "number_of_times_fallen": "NumberOfTimesFallen", "number_of_time_fallen": "NumberOfTimesFallen",
    "number_of_alcoholic_beverages": "NumberOfAlcoholicBeverages", "alcohol_consumption": "NumberOfAlcoholicBeverages",
    "uv_exposure": "UVExposure", "electrodermal_activity": "ElectrodermalActivity",
    "under_water_depth": "UnderwaterDepth", "underwater_depth": "UnderwaterDepth",
    "under_water_temperature": "WaterTemperature", "underwater_temperature": "WaterTemperature",
    # Nutrition
    "dietary_energy": "DietaryEnergyConsumed", "dietary_sugar": "DietarySugar", "sugar": "DietarySugar",
    "dietary_water": "DietaryWater", "water": "DietaryWater",
    "carbohydrates": "DietaryCarbohydrates", "protein": "DietaryProtein", "total_fat": "DietaryFatTotal",
    "saturated_fat": "DietaryFatSaturated", "polyunsaturated_fat": "DietaryFatPolyunsaturated",
    "monounsaturated_fat": "DietaryFatMonounsaturated", "monosaturated_fat": "DietaryFatMonounsaturated",
    "fiber": "DietaryFiber", "cholesterol": "DietaryCholesterol", "dietary_cholesterol": "DietaryCholesterol",
    "sodium": "DietarySodium", "potassium": "DietaryPotassium", "calcium": "DietaryCalcium", "iron": "DietaryIron",
    "magnesium": "DietaryMagnesium", "phosphorus": "DietaryPhosphorus", "zinc": "DietaryZinc", "copper": "DietaryCopper",
    "manganese": "DietaryManganese", "niacin": "DietaryNiacin", "pantothenic_acid": "DietaryPantothenicAcid",
    "chloride": "DietaryChloride", "thiamin": "DietaryThiamin", "riboflavin": "DietaryRiboflavin",
    "vitamin_b6": "DietaryVitaminB6", "vitamin_c": "DietaryVitaminC", "vitamin_e": "DietaryVitaminE",
    "caffeine": "DietaryCaffeine", "dietary_caffeine": "DietaryCaffeine",
    "folate": "DietaryFolate", "molybdenum": "DietaryMolybdenum", "selenium": "DietarySelenium",
    "vitamin_a": "DietaryVitaminA", "vitamin_b12": "DietaryVitaminB12", "vitamin_d": "DietaryVitaminD",
    "vitamin_k": "DietaryVitaminK", "iodine": "DietaryIodine", "chromium": "DietaryChromium",
    "biotin": "DietaryBiotin", "dietary_biotin": "DietaryBiotin",
}

_CATEGORY_NAMES: dict[str, str] = {
    "apple_stand_hour": "AppleStandHour",
    "mindful_minutes": "MindfulSession",
    "sexual_activity": "SexualActivity",
    "high_heart_rate_notifications": "HighHeartRateEvent",
    "low_heart_rate_notifications": "LowHeartRateEvent",
    "irregular_heart_rate_notifications": "IrregularHeartRhythmEvent",
}

#: Aggregated ``sleep_analysis`` fields (hours) → sleep metric keys.
SLEEP_FIELDS: dict[str, str] = {
    "totalSleep": "sleep.total", "asleep": "sleep.asleep", "core": "sleep.core",
    "deep": "sleep.deep", "rem": "sleep.rem", "awake": "sleep.awake",
    "inBed": "sleep.time_in_bed",
}
# fmt: on

#: Health Auto Export name → HealthKit identifier.
HAE_MAP: dict[str, str] = {
    **{name: f"{_Q}{hk}" for name, hk in _QUANTITY_NAMES.items()},
    **{name: f"{_C}{hk}" for name, hk in _CATEGORY_NAMES.items()},
}
