"""The model's remarks keep only the numbers the code computed."""

from __future__ import annotations

from app.services import meal_remarks

ITEMS = [
    {"name": "Tomate", "grams": 200, "protein_g": 1.4, "sodium_mg": 8},
    {"name": "Aubergines cuisinées à la provençale · Marque test · 185 g",
     "grams": 185, "food_id": "a", "sugars_g": 10.4, "sodium_mg": 562.4},
    {"name": "Saumon sauvage rose · 200 g", "grams": 100, "food_id": "s",
     "protein_g": 20.5, "fat_g": 4.4, "sodium_mg": 80},
]  # fmt: skip
TOTALS = {
    "protein_g": 24.6,
    "carbs_g": 22.7,
    "fiber_g": 6.6,
    "sodium_mg": 652.2,
}
SHEETS = [{"id": "s", "per_100g": {"sodium_mg": 80, "protein_g": 20.5}}]
KNOWN = meal_remarks.numbers(ITEMS, TOTALS, SHEETS)


def _clean(text: str) -> list[str]:
    return meal_remarks.clean([text], True, KNOWN)


def test_a_number_belongs_to_the_food_the_remark_names() -> None:
    # 24,6 g is the meal's protein, not the salmon's (20,5 g)
    assert _clean("Des protéines de qualité grâce au saumon (24,6 g).") == [
        "Des protéines de qualité grâce au saumon."
    ]
    assert _clean("Le saumon apporte 20,5 g de protéines.") == [
        "Le saumon apporte 20,5 g de protéines."
    ]
    assert _clean("Le saumon contient du sodium (80 mg/100g).") == [
        "Le saumon contient du sodium (80 mg/100g)."
    ]


def test_the_meal_s_totals_when_it_speaks_of_the_meal() -> None:
    both = (
        "Les aubergines sont salées (562,4 mg), une grande part du total "
        "du repas (652,2 mg)."
    )
    assert _clean(both) == [both]
    assert _clean("Des fibres (6,6 g) pour la satiété.") == [
        "Des fibres (6,6 g) pour la satiété."
    ]


def test_a_wrong_number_is_cut_and_a_doubt_too() -> None:
    assert _clean("Les aubergines sont salées (557 mg pour 185g).") == [
        "Les aubergines sont salées."
    ]
    assert _clean("Les aubergines apportent 557 mg de sodium.") == []
    assert _clean("Sodium des aubergines (vérifier l'étiquette réelle)") == [
        "Sodium des aubergines"
    ]


def test_a_long_remark_ends_at_a_full_sentence() -> None:
    long = "Une phrase complète pour commencer. " + "mot " * 100
    assert meal_remarks.short(long) == "Une phrase complète pour commencer."
    assert meal_remarks.short("mot " * 100).endswith("mot…")


EGGPLANT = {
    "id": "a",
    "open_food_facts": {
        "nova": 3,
        "fruits_veg_pct": 96.05,
        "ingredients": "Aubergines 60 %, tomates, oignons, huile d'olive, "
        "sucre (1,4 %), sel",
    },
}
DETAILED = meal_remarks.numbers(ITEMS, TOTALS, [*SHEETS, EGGPLANT])


def _checked(text: str) -> list[str]:
    return meal_remarks.clean([text], True, DETAILED)


def test_a_known_nova_group_is_named_right() -> None:
    assert _checked(
        "Le Nutri-Score de l'aliment ultra-transformé (aubergines) est A."
    ) == ["Le Nutri-Score de l'aliment transformé (aubergines) est A."]


def test_percentages_come_from_the_ingredients() -> None:
    kept = "Les aubergines contiennent du sucre ajouté (1,4 %)."
    assert _checked(kept) == [kept]
    assert _checked("Les aubergines : 96 % de légumes.") == [
        "Les aubergines : 96 % de légumes."
    ]
    assert _checked("Les aubergines contiennent du sucre ajouté (2,5 %).") == [
        "Les aubergines contiennent du sucre ajouté."
    ]


def test_added_sugar_needs_sugar_in_the_ingredients() -> None:
    plain = {**EGGPLANT, "open_food_facts": {"ingredients": "Aubergines, sel"}}
    known = meal_remarks.numbers(ITEMS, TOTALS, [*SHEETS, plain])
    said = "Les aubergines contiennent du sucre ajouté."
    assert meal_remarks.clean([said], True, known) == []


def test_a_nova_3_is_processed_but_not_ultra_processed() -> None:
    said = "Les aubergines, Nutri-Score A, ne sont pas transformées (NOVA 3)."
    assert _checked(said) == [
        "Les aubergines, Nutri-Score A, sont transformées (NOVA 3)."
    ]
    right = "Les aubergines ne sont pas ultra-transformées (NOVA 3)."
    assert _checked(right) == [right]


def test_salt_and_sodium_name_what_they_quote() -> None:
    comte = {"name": "Comté", "grams": 30, "sodium_mg": 120.9}
    known = meal_remarks.numbers([*ITEMS, comte], TOTALS, SHEETS)

    def clean(text: str) -> list[str]:
        return meal_remarks.clean([text], True, known)

    # 120,9 mg is the comté's sodium; its salt is 302 mg (× 2,5)
    assert clean("Comté : riche en sel (120,9 mg par 30g).") == [
        "Comté : riche en sodium (120,9 mg par 30g)."
    ]
    assert clean("Le comté apporte 302 mg de sel.") == [
        "Le comté apporte 302 mg de sel."
    ]
    assert clean("Le comté apporte 0,3 g de sodium.") == [
        "Le comté apporte 0,3 g de sel."
    ]
    assert clean("Sel des aubergines : 562,4 mg.") == [
        "Sodium des aubergines : 562,4 mg."
    ]
    right = "Aubergines riches en sel : 562,4 mg de sodium, soit 1,4 g de sel."
    assert clean(right) == [right]
    assert clean("Le repas apporte du sel (652,2 mg).") == [
        "Le repas apporte du sodium (652,2 mg)."
    ]
