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
