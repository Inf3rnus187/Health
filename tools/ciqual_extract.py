"""Extract the values the hub uses from the ANSES Ciqual table.

Source: « Anses. 2025. Table de composition nutritionnelle des aliments
Ciqual », Licence Ouverte / Etalab 2.0 — the French CSV published by
ANSES (tab separated, UTF-8; mirrored as
``external-data/ciqual/ciqual/CIQUAL2025_FR_2025_11_03.csv`` in the Open
Food Facts server repository). Usage::

    python tools/ciqual_extract.py CIQUAL2025_FR_2025_11_03.csv \
        > backend/app/data/ciqual.tsv

Output: one line per food — code, name, group, then per 100 g energy
(kcal, EU regulation 1169/2011), proteins (N x Jones), carbohydrates,
sugars, fat, saturated fatty acids, fibres, sodium (mg); ANSES notation
kept as text (``-`` unknown, ``traces``, ``< 0,5``), read by the hub.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

#: Output column → words its Ciqual header starts with (spaces collapsed).
COLUMNS = {
    "energy_kcal": "energie, reglement ue n° 1169 2011 (kcal",
    "protein_g": "proteines, n x facteur de jones (g",
    "carbs_g": "glucides (g",
    "sugars_g": "sucres (g",
    "fat_g": "lipides (g",
    "sat_fat_g": "ag satures (g",
    "fiber_g": "fibres alimentaires (g",
    "sodium_mg": "sodium (mg",
}
_ACCENTS = str.maketrans("éèêàâîïôûùç", "eeeaaiiouuc")


def _key(header: str) -> str:
    """A header on one line, lower case, without accents."""
    return re.sub(r"\s+", " ", header).strip().lower().translate(_ACCENTS)


def _columns(header: list[str]) -> dict[str, int]:
    """Where each needed value is, by header text (fails loudly)."""
    keys = [_key(h) for h in header]
    found = {"code": keys.index("alim_code"), "name": keys.index("alim_nom_fr")}
    found["group"] = keys.index("alim_ssgrp_nom_fr")
    for name, start in COLUMNS.items():
        match = [i for i, k in enumerate(keys) if k.startswith(start)]
        if len(match) != 1:
            raise SystemExit(f"{name}: {len(match)} columns start with {start!r}")
        found[name] = match[0]
    return found


def main(source: Path) -> None:
    """Write the extract on stdout, its provenance on stderr."""
    raw = source.read_bytes()
    rows = list(csv.reader(raw.decode("utf-8").splitlines(True), delimiter="\t"))
    at = _columns(rows[0])
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    out.writerow(["code", "name", "group", *COLUMNS])
    count = 0
    for row in rows[1:]:
        if len(row) < len(rows[0]) or not row[at["code"]].strip():
            continue
        values = [row[at[name]].strip() for name in COLUMNS]
        name = re.sub(r"\s+", " ", row[at["name"]]).strip()
        group = re.sub(r"\s+", " ", row[at["group"]]).strip()
        out.writerow([row[at["code"]].strip(), name, group, *values])
        count += 1
    digest = hashlib.sha256(raw).hexdigest()
    print(f"{count} foods from {source.name} (sha256 {digest})", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
