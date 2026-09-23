"""Which indicators follow which condition (data file).

A declared condition is matched on keywords of its name (accent- and
case-insensitive), so "Stéatose hépatique S3", "MASLD" or "foie gras"
all bring the FibroScan, liver enzymes, weight and waist. Keys are the
canonical metric keys every page reads. Long lines are allowed here.
"""

from __future__ import annotations

from app.services.textfold import fold

# fmt: off
_LIVER = ("liver.cap", "liver.lsm", "bio.alat", "bio.asat", "bio.ggt", "bio.triglycerides", "body.weight", "body.waist")
_GLUCOSE = ("bio.hba1c", "bio.glycemie", "body.weight", "body.waist", "bio.triglycerides", "nutrition.energy", "elimination.urination")
_LIPIDS = ("bio.cholesterol_ldl", "bio.cholesterol_hdl", "bio.cholesterol_non_hdl", "bio.cholesterol_total", "bio.triglycerides")
_BREATH = ("symptom.breath", "symptom.cough", "body.spo2", "body.resp_rate", "habit.cigarettes")

#: (keywords, indicator keys) — every matching line adds its indicators.
LINKS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("steatose", "steatopathie", "foie gras", "masld", "mash", "nafld", "nash", "hepat", "foie", "cirrhose", "fibrose"), _LIVER),
    (("diabete", "diabetique", "prediabete", "hyperglycemie", "insulinoresistance", "insulino-resistance", "glycemie"), _GLUCOSE),
    (("dyslipidemie", "cholesterol", "hypercholesterolemie", "triglyceride", "hypertriglyceridemie"), _LIPIDS),
    (("obesite", "surpoids", "syndrome metabolique"), ("body.weight", "body.waist", "body.bmi", "body.fat_pct", "bio.hba1c", "bio.triglycerides")),
    (("hypertension", "hta", "tension arterielle"), ("vitals.bp_systolic", "vitals.bp_diastolic", "rest.hr", "body.weight", "bio.potassium", "bio.creatinine")),
    (("apnee", "saos", "sahos", "sas "), ("ppc.ahi", "ppc.hours_used", "ppc.leak_median", "body.spo2", "state.fatigue", "body.weight", "elimination.urination")),
    (("tabac", "tabagisme", "fumeur", "nicotin", "sevrage tabagique"), ("habit.cigarettes", "habit.urges_broken", "symptom.breath", "symptom.cough", "body.spo2")),
    (("bpco", "asthme", "emphyseme", "bronch", "insuffisance respiratoire", "dyspnee"), _BREATH),
    (("cardiaque", "coronar", "infarctus", "fibrillation", "arythmie", "insuffisance cardiaque"), ("heart.rate", "rest.hr", "heart.hrv", "vitals.bp_systolic", "vitals.bp_diastolic", "body.weight", "fitness.vo2max")),
    (("depress", "anxi", "burn", "insomnie", "trouble du sommeil"), ("state.mood_energy", "state.fatigue", "sleep.asleep", "heart.hrv")),
    (("renal", "rein", "nephro"), ("bio.creatinine", "bio.uree", "bio.potassium", "bio.sodium", "vitals.bp_systolic")),
    (("anemie", "carence en fer", "carence martiale"), ("bio.hemoglobine", "bio.ferritine", "bio.fer", "bio.vgm")),
    (("thyroid",), ("bio.tsh", "body.weight", "rest.hr")),
    (("goutte", "hyperuricemie", "acide urique"), ("bio.acide_urique", "bio.creatinine")),
    (("vitamine d",), ("bio.vitamine_d", "bio.calcium")),
    (("inflamm", "infection"), ("bio.crp", "bio.leucocytes", "vitals.body_temp")),
)
# fmt: on


def indicators_for(name: str) -> list[str]:
    """Indicator keys of a condition, in order, without duplicates."""
    folded = f" {fold(name)} "
    keys: list[str] = []
    for words, linked in LINKS:
        if any(word in folded for word in words):
            keys.extend(k for k in linked if k not in keys)
    return keys
