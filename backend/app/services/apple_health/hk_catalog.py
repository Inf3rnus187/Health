"""Every public HealthKit sample type (iOS 26 SDK), in French (data file).

Generated from the iOS SDK headers (react-native-healthkit's schema and
the .NET HealthKit bindings agree on 121 quantity / 72 category types,
3 of which are iOS 27). The 28 types curated in :mod:`spec` keep their
historical keys; every other type is stored under ``apple.<slug>`` —
the key a synthesized spec always used — so nothing already imported
moves, but each now gets a French label, a Health-app domain, the unit
the French export uses and its daily aggregation (sum for cumulative
types, average for discrete ones).

Categories carry a value family telling how an event becomes a number
(see :mod:`hk_values`): a symptom's severity 0-3, a flow 0-3, a count
of 1 per event, or a duration in minutes (mindfulness).
Long lines are allowed here (data, not logic).
"""

from __future__ import annotations

from typing import NamedTuple

_Q = "HKQuantityTypeIdentifier"
_C = "HKCategoryTypeIdentifier"


class HkType(NamedTuple):
    """How to store one HealthKit type."""

    label: str
    domain: str
    unit: str | None
    agg: str
    family: str = ""


# fmt: off
_QUANTITIES: dict[str, HkType] = {
    # Activité
    "AppleMoveTime": HkType("Minutes de mouvement", "activity", "min", "sum"),
    "DistanceSwimming": HkType("Distance de natation", "activity", "m", "sum"),
    "DistanceWheelchair": HkType("Distance en fauteuil roulant", "activity", "km", "sum"),
    "DistanceDownhillSnowSports": HkType("Distance en sports de neige", "activity", "km", "sum"),
    "DistanceCrossCountrySkiing": HkType("Distance en ski de fond", "activity", "km", "sum"),
    "DistancePaddleSports": HkType("Distance en sports de pagaie", "activity", "km", "sum"),
    "DistanceRowing": HkType("Distance d'aviron", "activity", "km", "sum"),
    "DistanceSkatingSports": HkType("Distance en patinage", "activity", "km", "sum"),
    "PushCount": HkType("Poussées en fauteuil roulant", "activity", "count", "sum"),
    "SwimmingStrokeCount": HkType("Mouvements de nage", "activity", "count", "sum"),
    "NikeFuel": HkType("NikeFuel", "activity", "count", "sum"),
    "PhysicalEffort": HkType("Effort physique (MET)", "activity", "kcal/hr·kg", "avg"),
    "WorkoutEffortScore": HkType("Effort de l'entraînement", "activity", "appleEffortScore", "avg"),
    "EstimatedWorkoutEffortScore": HkType("Effort estimé de l'entraînement", "activity", "appleEffortScore", "avg"),
    "RunningSpeed": HkType("Vitesse de course", "activity", "km/hr", "avg"),
    "RunningPower": HkType("Puissance de course", "activity", "W", "avg"),
    "RunningStrideLength": HkType("Longueur de foulée", "activity", "m", "avg"),
    "RunningVerticalOscillation": HkType("Oscillation verticale", "activity", "cm", "avg"),
    "RunningGroundContactTime": HkType("Temps de contact au sol", "activity", "ms", "avg"),
    "CyclingSpeed": HkType("Vitesse à vélo", "activity", "km/hr", "avg"),
    "CyclingPower": HkType("Puissance à vélo", "activity", "W", "avg"),
    "CyclingCadence": HkType("Cadence de pédalage", "activity", "count/min", "avg"),
    "CyclingFunctionalThresholdPower": HkType("Puissance seuil fonctionnelle (FTP)", "activity", "W", "avg"),
    "CrossCountrySkiingSpeed": HkType("Vitesse en ski de fond", "activity", "km/hr", "avg"),
    "PaddleSportsSpeed": HkType("Vitesse en sports de pagaie", "activity", "km/hr", "avg"),
    "RowingSpeed": HkType("Vitesse d'aviron", "activity", "km/hr", "avg"),
    # Audition
    "EnvironmentalAudioExposure": HkType("Niveaux sonores environnementaux", "hearing", "dBASPL", "avg"),
    "HeadphoneAudioExposure": HkType("Niveaux sonores des écouteurs", "hearing", "dBASPL", "avg"),
    "EnvironmentalSoundReduction": HkType("Réduction du bruit", "hearing", "dBASPL", "avg"),
    # Cœur
    "HeartRateRecoveryOneMinute": HkType("Récupération cardio (1 min)", "heart", "count/min", "avg"),
    "HeartRateVariabilityRMSSD": HkType("Variabilité cardiaque (RMSSD)", "heart", "ms", "avg"),
    "AtrialFibrillationBurden": HkType("Historique de fibrillation atriale", "heart", "%", "avg"),
    # Mobilité
    "AppleWalkingSteadiness": HkType("Stabilité de la marche", "mobility", "%", "avg"),
    "SixMinuteWalkTestDistance": HkType("Test de marche de 6 minutes", "mobility", "m", "avg"),
    "StairAscentSpeed": HkType("Vitesse dans les escaliers : montée", "mobility", "m/s", "avg"),
    "StairDescentSpeed": HkType("Vitesse dans les escaliers : descente", "mobility", "m/s", "avg"),
    "WalkingSpeed": HkType("Vitesse de marche", "mobility", "km/hr", "avg"),
    "WalkingStepLength": HkType("Longueur des pas", "mobility", "cm", "avg"),
    "WalkingAsymmetryPercentage": HkType("Asymétrie de la marche", "mobility", "%", "avg"),
    "WalkingDoubleSupportPercentage": HkType("Temps de double appui", "mobility", "%", "avg"),
    # Respiration
    "ForcedVitalCapacity": HkType("Capacité vitale forcée", "respiratory", "L", "avg"),
    "ForcedExpiratoryVolume1": HkType("VEMS", "respiratory", "L", "avg"),
    "PeakExpiratoryFlowRate": HkType("Débit expiratoire de pointe", "respiratory", "L/min", "avg"),
    "InhalerUsage": HkType("Utilisation d'inhalateur", "respiratory", "count", "sum"),
    "AppleSleepingBreathingDisturbances": HkType("Troubles respiratoires (sommeil)", "respiratory", "count", "avg"),
    # Cycle
    "BasalBodyTemperature": HkType("Température basale", "cycle", "°C", "avg"),
    # Autres données
    "TimeInDaylight": HkType("Temps à la lumière du jour", "other", "min", "sum"),
    "BloodAlcoholContent": HkType("Taux d'alcoolémie", "other", "%", "avg"),
    "NumberOfAlcoholicBeverages": HkType("Boissons alcoolisées", "other", "count", "sum"),
    "NumberOfTimesFallen": HkType("Nombre de chutes", "other", "count", "sum"),
    "InsulinDelivery": HkType("Insuline administrée", "other", "IU", "sum"),
    "ElectrodermalActivity": HkType("Activité électrodermale", "other", "mcS", "avg"),
    "PeripheralPerfusionIndex": HkType("Indice de perfusion", "other", "%", "avg"),
    "UVExposure": HkType("Exposition aux UV", "other", "count", "avg"),
    "UnderwaterDepth": HkType("Profondeur sous l'eau", "other", "m", "avg"),
    "WaterTemperature": HkType("Température de l'eau", "other", "°C", "avg"),
    # Nutrition (grammes)
    "DietaryCarbohydrates": HkType("Glucides", "nutrition", "g", "sum"),
    "DietaryFiber": HkType("Fibres", "nutrition", "g", "sum"),
    "DietarySugar": HkType("Sucres", "nutrition", "g", "sum"),
    "DietaryProtein": HkType("Protéines", "nutrition", "g", "sum"),
    "DietaryFatTotal": HkType("Lipides", "nutrition", "g", "sum"),
    "DietaryFatSaturated": HkType("Acides gras saturés", "nutrition", "g", "sum"),
    "DietaryFatMonounsaturated": HkType("Acides gras mono-insaturés", "nutrition", "g", "sum"),
    "DietaryFatPolyunsaturated": HkType("Acides gras polyinsaturés", "nutrition", "g", "sum"),
    # Nutrition (milligrammes)
    "DietaryCholesterol": HkType("Cholestérol alimentaire", "nutrition", "mg", "sum"),
    "DietarySodium": HkType("Sodium", "nutrition", "mg", "sum"),
    "DietaryPotassium": HkType("Potassium", "nutrition", "mg", "sum"),
    "DietaryCalcium": HkType("Calcium", "nutrition", "mg", "sum"),
    "DietaryIron": HkType("Fer", "nutrition", "mg", "sum"),
    "DietaryMagnesium": HkType("Magnésium", "nutrition", "mg", "sum"),
    "DietaryPhosphorus": HkType("Phosphore", "nutrition", "mg", "sum"),
    "DietaryZinc": HkType("Zinc", "nutrition", "mg", "sum"),
    "DietaryCopper": HkType("Cuivre", "nutrition", "mg", "sum"),
    "DietaryManganese": HkType("Manganèse", "nutrition", "mg", "sum"),
    "DietaryChloride": HkType("Chlorure", "nutrition", "mg", "sum"),
    "DietaryThiamin": HkType("Vitamine B1 (thiamine)", "nutrition", "mg", "sum"),
    "DietaryRiboflavin": HkType("Vitamine B2 (riboflavine)", "nutrition", "mg", "sum"),
    "DietaryNiacin": HkType("Vitamine B3 (niacine)", "nutrition", "mg", "sum"),
    "DietaryPantothenicAcid": HkType("Vitamine B5 (acide pantothénique)", "nutrition", "mg", "sum"),
    "DietaryVitaminB6": HkType("Vitamine B6", "nutrition", "mg", "sum"),
    "DietaryVitaminC": HkType("Vitamine C", "nutrition", "mg", "sum"),
    "DietaryVitaminE": HkType("Vitamine E", "nutrition", "mg", "sum"),
    "DietaryCaffeine": HkType("Caféine", "nutrition", "mg", "sum"),
    # Nutrition (microgrammes)
    "DietaryVitaminA": HkType("Vitamine A", "nutrition", "mcg", "sum"),
    "DietaryVitaminD": HkType("Vitamine D (apport)", "nutrition", "mcg", "sum"),
    "DietaryVitaminK": HkType("Vitamine K", "nutrition", "mcg", "sum"),
    "DietaryVitaminB12": HkType("Vitamine B12 (apport)", "nutrition", "mcg", "sum"),
    "DietaryFolate": HkType("Folates (B9)", "nutrition", "mcg", "sum"),
    "DietaryBiotin": HkType("Biotine (B8)", "nutrition", "mcg", "sum"),
    "DietaryIodine": HkType("Iode", "nutrition", "mcg", "sum"),
    "DietarySelenium": HkType("Sélénium", "nutrition", "mcg", "sum"),
    "DietaryChromium": HkType("Chrome", "nutrition", "mcg", "sum"),
    "DietaryMolybdenum": HkType("Molybdène", "nutrition", "mcg", "sum"),
}

_SEV = ("symptom", "/3", "max", "severity")
_SYMPTOMS = {
    "AbdominalCramps": "Crampes abdominales", "Acne": "Acné",
    "BladderIncontinence": "Incontinence urinaire", "Bloating": "Ballonnements",
    "BreastPain": "Douleurs mammaires", "ChestTightnessOrPain": "Oppression ou douleur thoracique",
    "Chills": "Frissons", "Constipation": "Constipation", "Coughing": "Toux",
    "Diarrhea": "Diarrhée", "Dizziness": "Vertiges", "DrySkin": "Peau sèche",
    "Fainting": "Évanouissement", "Fatigue": "Fatigue", "Fever": "Fièvre",
    "GeneralizedBodyAche": "Courbatures", "HairLoss": "Perte de cheveux",
    "Headache": "Maux de tête", "Heartburn": "Brûlures d'estomac",
    "HotFlashes": "Bouffées de chaleur", "LossOfSmell": "Perte d'odorat",
    "LossOfTaste": "Perte du goût", "LowerBackPain": "Douleurs lombaires",
    "MemoryLapse": "Trous de mémoire", "Nausea": "Nausées", "NightSweats": "Sueurs nocturnes",
    "PelvicPain": "Douleurs pelviennes", "RapidPoundingOrFlutteringHeartbeat": "Palpitations",
    "RunnyNose": "Nez qui coule", "ShortnessOfBreath": "Essoufflement",
    "SinusCongestion": "Congestion des sinus", "SkippedHeartbeat": "Battements cardiaques manqués",
    "SoreThroat": "Mal de gorge", "VaginalDryness": "Sécheresse vaginale",
    "Vomiting": "Vomissements", "Wheezing": "Respiration sifflante",
}

_CATEGORIES: dict[str, HkType] = {
    **{name: HkType(label, *_SEV) for name, label in _SYMPTOMS.items()},
    "MoodChanges": HkType("Sautes d'humeur", "symptom", None, "max", "presence"),
    "SleepChanges": HkType("Troubles du sommeil", "symptom", None, "max", "presence"),
    "AppetiteChanges": HkType("Changements d'appétit", "symptom", None, "max", "appetite"),
    "AppleStandHour": HkType("Heures debout", "activity", "h", "sum", "stand"),
    "AppleWalkingSteadinessEvent": HkType("Alerte de stabilité de la marche", "mobility", "count", "sum", "count"),
    "AudioExposureEvent": HkType("Exposition sonore (ancien)", "hearing", "count", "sum", "count"),
    "EnvironmentalAudioExposureEvent": HkType("Notification de bruit", "hearing", "count", "sum", "count"),
    "HeadphoneAudioExposureEvent": HkType("Notification des écouteurs", "hearing", "count", "sum", "count"),
    "HighHeartRateEvent": HkType("Notification de FC élevée", "heart", "count", "sum", "count"),
    "LowHeartRateEvent": HkType("Notification de FC basse", "heart", "count", "sum", "count"),
    "IrregularHeartRhythmEvent": HkType("Notification de rythme irrégulier", "heart", "count", "sum", "count"),
    "HypertensionEvent": HkType("Notification d'hypertension", "heart", "count", "sum", "count"),
    "LowCardioFitnessEvent": HkType("Notification de forme cardio faible", "heart", "count", "sum", "count"),
    "SleepApneaEvent": HkType("Notification d'apnée du sommeil", "sleep", "count", "sum", "count"),
    "MindfulSession": HkType("Pleine conscience", "mindfulness", "min", "sum", "duration"),
    "HandwashingEvent": HkType("Lavage des mains", "other", "count", "sum", "count"),
    "ToothbrushingEvent": HkType("Brossage des dents", "other", "count", "sum", "count"),
    "MenstrualFlow": HkType("Règles (flux)", "cycle", "/3", "max", "flow"),
    "BleedingDuringPregnancy": HkType("Saignements pendant la grossesse", "cycle", "/3", "max", "flow"),
    "BleedingAfterPregnancy": HkType("Saignements après la grossesse", "cycle", "/3", "max", "flow"),
    "BleedingAfterMenopause": HkType("Saignements après la ménopause", "cycle", "/3", "max", "flow"),
    "IntermenstrualBleeding": HkType("Saignements intermenstruels", "cycle", "count", "sum", "count"),
    "PersistentIntermenstrualBleeding": HkType("Spotting persistant", "cycle", "count", "sum", "count"),
    "InfrequentMenstrualCycles": HkType("Cycles peu fréquents", "cycle", "count", "sum", "count"),
    "IrregularMenstrualCycles": HkType("Cycles irréguliers", "cycle", "count", "sum", "count"),
    "ProlongedMenstrualPeriods": HkType("Règles prolongées", "cycle", "count", "sum", "count"),
    "CervicalMucusQuality": HkType("Glaire cervicale", "cycle", "/5", "last", "mucus"),
    "OvulationTestResult": HkType("Test d'ovulation", "cycle", None, "max", "test"),
    "PregnancyTestResult": HkType("Test de grossesse", "cycle", None, "max", "test"),
    "ProgesteroneTestResult": HkType("Test de progestérone", "cycle", None, "max", "test"),
    "Contraceptive": HkType("Contraception", "cycle", "count", "last", "count"),
    "SexualActivity": HkType("Activité sexuelle", "cycle", "count", "sum", "count"),
    "Lactation": HkType("Allaitement", "cycle", "count", "last", "count"),
    "Pregnancy": HkType("Grossesse", "cycle", "count", "last", "count"),
    "MenopausalState": HkType("Statut ménopausique", "cycle", None, "last", "menopause"),
}
# fmt: on

#: Full identifier → storage description.
TYPES: dict[str, HkType] = {
    **{f"{_Q}{name}": spec for name, spec in _QUANTITIES.items()},
    **{f"{_C}{name}": spec for name, spec in _CATEGORIES.items()},
}

#: French names of the Health-app domains used as dashboard tabs.
DOMAINS = {
    "activity": "Activité",
    "body": "Mesures corporelles",
    "cycle": "Suivi du cycle",
    "hearing": "Audition",
    "heart": "Cœur",
    "mobility": "Mobilité",
    "nutrition": "Nutrition",
    "respiratory": "Respiration",
    "sleep": "Sommeil",
    "symptom": "Symptômes",
    "vitals": "Signes vitaux",
    "mindfulness": "Pleine conscience",
    "other": "Autres données",
}
