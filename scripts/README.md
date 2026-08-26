# Script index, by scientific stage

Scripts are kept flat and at their historical paths, since frozen
documents and commit messages reference them by path. This index groups
them. The full pipeline narrative with inputs, outputs, and status is
`docs/REPRODUCING.md`.

**💸 = makes paid external API calls. Everything else is local and safe.**

## Synthetic validation
No scripts here. The synthetic study is the `offcriterion` /
`evaluator-audit` CLI in `src/offcriterion/`.

## Data preparation
- `prepare_persuade.py` rebuilds the derived corpus inputs from the raw
  PERSUADE CSVs and verifies byte exact SHA-256 reproduction.

## Feasibility and power (design stage)
- `persuade_feasibility.py`, `persuade_power_planning.py`,
  `persuade_power_extra.py`, `persuade_fill_report.py`: v1 design
  evidence covering both tasks, behind `docs/persuade_feasibility.md`.
  Superseded.
- `persuade_feasibility_independent.py`, `persuade_power_independent.py`:
  v2, Independent task only, the operative confirmatory design (prereg v2).

## Pipeline validation (before scoring)
- `dry_run.py`: full pipeline run with a fake deterministic evaluator (no API).

## Confirmatory pipeline
- `run_primary_scoring.py` 💸: GPT-5.4-mini standard prompt census scoring.
- `run_secondary_scoring.py` 💸: the `haiku_plain`, `gemini_plain`, and
  `gpt_ignore` cells.
- `stage_d_freeze.py`, `stage_d_freeze_secondary.py`: freeze a store with
  a checksum manifest.
- `stage_e_analysis.py`: preregistered primary analysis.
- `stage_e_secondary.py`: preregistered secondary cell analyses.
- `negative_control.py`: preregistered negative control.
- `holm_secondary_family.py`: Holm summary of the secondary family.
- `verify_information_barrier.py`: confirm no demographic entered any prompt.

## Post hoc (clearly labeled, never confirmatory)
- `posthoc_exclusion_audit.py`: technical exclusion sensitivity audit.
- `posthoc_quality_index.py`: Stage 1, human discourse quality index
  (frozen before any join).
- `posthoc_feasibility.py`: Stages 2 and 4, Z1/Z2 feasibility gates and
  frozen bins.
- `posthoc_robustness_tests.py`: Stages 3 and 4, G² tests under richer
  conditioning.
- `posthoc_validity.py`: Stage 5, evaluator vs human alignment metrics.
- `posthoc_paired.py`: Stage 6, paired analysis of the standard and
  modified prompt cells.
