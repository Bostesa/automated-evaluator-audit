# PERSUADE 2.0 — data provenance

**Not committed to git** (large files; CC BY-NC-SA 4.0 redistribution kept to
the canonical source). Re-obtain as below.

## Source

- Canonical repository: https://github.com/scrosseye/persuade_corpus_2.0
  (Scott Crossley / The Learning Agency Lab). The repository's README links
  the CSVs, which are too large for GitHub:
  - Training set: Google Drive id `13phHyDzIsb0MHyJr6q-B-qIa9P2tM135`
    → `persuade_train.csv`
  - Test set: Google Drive id `1K1SIJiG-2zWgMlTzxQeYOcLwOsFaVel1`
    → `persuade_test.zip` (password `persuade_test`, published in the
    canonical README) → `persuade_corpus_2.0_test.csv`
- Downloaded: 2026-08-25.
- SHA-256:
  - `persuade_train.csv`: `f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23`
  - `persuade_test.zip`: `51c907f90b1303d610e8fcd8c0cbf3656ec88116bc34b60b93794affa77facb2`
- Version: PERSUADE 2.0 (the corpus release described in Crossley, S. A.,
  Baffour, P., Tian, Y., Franklin, A., Benner, M., & Boser, U. (2024). A
  large-scale corpus for assessing written argumentation: PERSUADE 2.0.
  *Assessing Writing*, 61.)
- License: **CC BY-NC-SA 4.0** (stated in the canonical repository README).
  This project's use is non-commercial research.

## Derived file

`persuade_essay_level.csv` — produced by deduplicating the two
discourse-element-level CSVs (285,383 rows total) to one row per unique
`essay_id_comp` (25,996 essays), keeping essay-level metadata plus a SHA-1 of
`full_text`. Metadata was verified constant across the discourse rows of every
essay (0 conflicts). Note the numeric `essay_id` column is Excel-mangled
scientific notation and is NOT unique; `essay_id_comp` is the reliable key.

## Regenerating the derived files

All three derived inputs (`persuade_essay_level.csv`, `essay_texts.csv`,
`prompt_materials.csv`) are reconstructed deterministically from the two raw
corpus CSVs by:

    python scripts/prepare_persuade.py --out-dir data/persuade

By default the script writes to `data/persuade/prepared/` so existing copies
are never overwritten. It verifies its outputs against the recorded SHA-256
values (byte-exact reproduction confirmed 2026-08-26):

- `persuade_essay_level.csv`: `b45aa58f7c4b4d9018511515cd1cf1dd409299ea093329272a05571f8203be8f`
- `essay_texts.csv`: `df3b411a8644e81e72289d96baae59aa75a5e49805008aa58a7231ff4330f0d7`
- `prompt_materials.csv`: `2e169ec033627459e4199750710143cbf87e693a5a78de76a53fafe0bb71e0e6`
