# Reference data shipped with the hub

## `ciqual.tsv` — table Ciqual 2025 (ANSES)

- **Source**: « Anses. 2025. Table de composition nutritionnelle des
  aliments Ciqual » — https://ciqual.anses.fr — published 2025-11-03.
- **Licence**: Licence Ouverte / Etalab 2.0 (reuse allowed with
  attribution: the source and its date above).
- **File extracted**: `CIQUAL2025_FR_2025_11_03.csv` (French CSV,
  tab separated, UTF-8), as mirrored in the Open Food Facts server
  repository (`external-data/ciqual/ciqual/`), sha256
  `013a82d94e7c29a165a25494dd9ad45cfed64de902602c2e479a4a06ea23990a`.
- **Extract**: 3,484 foods — code, name, sub-group, and per 100 g:
  energy (kcal, EU regulation 1169/2011), proteins (N × Jones factor),
  carbohydrates, sugars, fat, saturated fatty acids, fibres, sodium
  (mg). ANSES notation kept: `-` unknown, `traces`, `< x`.
- **Regenerate** (a newer table): `python tools/ciqual_extract.py
  <CIQUAL…_FR_….csv> > backend/app/data/ciqual.tsv`; the script prints
  the count and the sha256 of its source — update this file and
  `VERSION` in `app/services/ciqual.py`.

Used offline by `app/services/ciqual.py`: nothing is downloaded or sent
at run time.
