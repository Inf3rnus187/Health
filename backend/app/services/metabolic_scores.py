"""Validated anthropometric and biological scores (pure formulas).

* WHtR — waist-to-height ratio (Ashwell 2012): best simple anthropometric
  marker of visceral fat and cardiometabolic risk; boundary 0.5.
* FLI — Fatty Liver Index (Bedogni 2006): steatosis probability from
  triglycerides, BMI, GGT and waist; < 30 rules out, >= 60 rules in.
* FIB-4 (Sterling 2006): advanced liver fibrosis from age, AST, ALT and
  platelets; < 1.30 (< 2.0 from age 65) rules out, >= 2.67 high.
* TyG (Simental-Mendía 2008): insulin-resistance index from fasting
  triglycerides and glucose (indicative, thresholds not consensual).

French labs report triglycerides and glucose in g/L; the formulas are
defined in mg/dL (x 100).
"""

from __future__ import annotations

import math

_MG_PER_DL = 100.0


def whtr(waist_cm: float, height_cm: float) -> float:
    """Waist-to-height ratio."""
    return waist_cm / height_cm


def bmi(weight_kg: float, height_cm: float) -> float:
    """Body-mass index (kg/m²)."""
    return weight_kg / (height_cm / 100.0) ** 2


def fli(tg_g_l: float, bmi_value: float, ggt_u_l: float, waist: float) -> float:
    """Fatty Liver Index (0-100) from TG (g/L), BMI, GGT (U/L), waist (cm)."""
    y = (
        0.953 * math.log(tg_g_l * _MG_PER_DL)
        + 0.139 * bmi_value
        + 0.718 * math.log(ggt_u_l)
        + 0.053 * waist
        - 15.745
    )
    return 100.0 / (1.0 + math.exp(-y))


def fib4(age: float, ast: float, alt: float, platelets_g_l: float) -> float:
    """FIB-4 from age (years), AST/ALT (U/L) and platelets (G/L)."""
    return (age * ast) / (platelets_g_l * math.sqrt(alt))


def tyg(tg_g_l: float, glucose_g_l: float) -> float:
    """Triglyceride-glucose index from fasting TG and glucose (g/L)."""
    return math.log(tg_g_l * _MG_PER_DL * glucose_g_l * _MG_PER_DL / 2.0)
