# Data and licensing

This repository mixes original code, third-party corpus-derived artifacts,
and raw outputs from commercial model APIs. The applicable terms differ.

## Repository-authored code — MIT

All original code (everything under `src/`, `scripts/`, `tests/`, and the
documentation) is licensed under the MIT license (`LICENSE`).

## PERSUADE 2.0 corpus — CC BY-NC-SA 4.0 (not redistributed)

The PERSUADE 2.0 corpus (Crossley et al., 2024, *Assessing Writing* 61) is
licensed CC BY-NC-SA 4.0 by its authors. **This repository does not
redistribute the corpus**: no essay text, no raw corpus file, and no
password-protected archive is tracked. `data/persuade/README.md` records the
canonical download locations and SHA-256 hashes;
`scripts/prepare_persuade.py` rebuilds the derived working files locally.

Some **tracked artifacts are derived from corpus metadata** — essay-ID
sample manifests, per-essay aggregate quality indices, per-essay stratum bin
assignments, and stratum-level feasibility tables. They contain corpus
identifiers and derived numbers, never essay text. To the extent these count
as adaptations of the corpus, they remain subject to CC BY-NC-SA 4.0
(attribution: The Learning Agency Lab / Crossley et al.; non-commercial;
share-alike) rather than this repository's MIT license.

## Evaluator (model API) outputs — research evidence, not relicensed

`data/scoring/` contains verbatim raw responses from OpenAI, Anthropic, and
Google model APIs (each response is a JSON object with a single 1–6 score),
published as frozen research evidence with checksum manifests. These are
provider outputs subject to the respective providers' terms; including them
here does not relicense them as original code. No provider credentials,
request headers, or essay text appear in these stores.

## Human subjects note

The corpus's demographic fields (including ELL status) are used only in the
statistical analyses described in the preregistration, never in prompt
construction (enforced structurally and verified per-record by
`scripts/verify_information_barrier.py`). Tracked artifacts contain no essay
text and no per-person information beyond what the corpus itself publishes
under its license.
