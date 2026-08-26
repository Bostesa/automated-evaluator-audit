# Data and licensing

This repository mixes original code, artifacts derived from a third
party corpus, and raw outputs from commercial model APIs. The applicable
terms differ.

## Repository code (MIT)

All original code (everything under `src/`, `scripts/`, `tests/`, and the
documentation) is licensed under the MIT license (`LICENSE`).

## PERSUADE 2.0 corpus (CC BY-NC-SA 4.0, not redistributed)

The PERSUADE 2.0 corpus (Crossley et al., 2024, *Assessing Writing* 61)
is licensed CC BY-NC-SA 4.0 by its authors. This repository does not
redistribute the corpus. No essay text, raw corpus file, or password
protected archive is tracked. `data/persuade/README.md` records the
canonical download locations and SHA-256 hashes, and
`scripts/prepare_persuade.py` rebuilds the derived working files locally.

Some tracked artifacts are derived from corpus metadata. These are the
essay ID sample manifests, the aggregate quality indices and stratum bin
assignments for each essay, and the stratum level feasibility tables.
They contain corpus identifiers and derived numbers, never essay text. To
the extent these count as adaptations of the corpus, they remain subject
to CC BY-NC-SA 4.0 (attribution to The Learning Agency Lab / Crossley et
al., non-commercial use, share-alike) rather than this repository's MIT
license.

## Evaluator (model API) outputs (research evidence, not relicensed)

`data/scoring/` contains verbatim raw responses from OpenAI, Anthropic,
and Google model APIs (each response is a JSON object with a single 1–6
score), published as frozen research evidence with checksum manifests.
These are provider outputs subject to the respective providers' terms.
Including them here does not relicense them as original code. No provider
credentials, request headers, or essay text appear in these stores.

## Human subjects note

The corpus's demographic fields (including ELL status) are used only in
the statistical analyses described in the preregistration, never in
prompt construction. This is enforced structurally and verified record by
record by `scripts/verify_information_barrier.py`. Tracked artifacts
contain no essay text and no information about individual writers beyond
what the corpus itself publishes under its license.
