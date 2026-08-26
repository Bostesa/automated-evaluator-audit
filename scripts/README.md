# Script index, by scientific stage

Scripts are kept flat and at their historical paths (several are referenced
by frozen documents and commit messages). This index groups them; the full
pipeline narrative with inputs/outputs/status is `docs/REPRODUCING.md`.

**💸 = makes paid external API calls. Everything else is local and safe.**

## Synthetic validation
(no scripts here — the synthetic study is the `offcriterion` /
`evaluator-audit` CLI in `src/offcriterion/`)

## Data preparation
- `prepare_persuade.py` — rebuild the derived corpus inputs from the raw
  PERSUADE CSVs; verifies byte-exact SHA-256 reproduction

## Feasibility & power (design stage)
- `persuade_feasibility.py`, `persuade_power_planning.py`,
  `persuade_power_extra.py`, `persuade_fill_report.py` — **v1 (both tasks);
  superseded** design-stage evidence behind `docs/persuade_feasibility.md`
- `persuade_feasibility_independent.py`, `persuade_power_independent.py` —
  **v2 (Independent-only); the operative confirmatory design** (prereg v2)

## Pipeline validation (pre-scoring)
- `dry_run.py` — end-to-end run with a fake deterministic judge (no API)

## Confirmatory pipeline
- `run_primary_scoring.py` 💸 — GPT-5.4-mini plain-rubric census scoring
- `run_secondary_scoring.py` 💸 — Haiku plain / Gemini plain / GPT ignore cells
- `stage_d_freeze.py`, `stage_d_freeze_secondary.py` — checksum-freeze a store
- `stage_e_analysis.py` — preregistered primary analysis
- `stage_e_secondary.py` — preregistered secondary-cell analyses
- `negative_control.py` — preregistered negative control
- `holm_secondary_family.py` — Holm-corrected secondary family summary
- `verify_information_barrier.py` — prove no demographic entered any prompt

## Post-hoc (clearly labeled, never confirmatory)
- `posthoc_exclusion_audit.py` — technical-exclusion sensitivity audit
- `posthoc_quality_index.py` — Stage 1: human discourse-quality index (frozen pre-join)
- `posthoc_feasibility.py` — Stage 2/4: Z1/Z2 feasibility gates + frozen bins
- `posthoc_robustness_tests.py` — Stage 3/4: richer-conditioning G² tests
- `posthoc_validity.py` — Stage 5: judge-vs-human alignment metrics
- `posthoc_paired.py` — Stage 6: paired plain vs ignore-demographics analysis
