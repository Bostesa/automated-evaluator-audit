# Environments that produced the reported results

Exact historical environments are recorded for the audit trail. The code
is not believed to require them (dependencies are declared with loose
lower bounds in `pyproject.toml`, and results are seed deterministic).

## Synthetic validation, scoring pipeline, and confirmatory analyses

Project virtualenv (`.venv`, editable install), used for the synthetic
study, the dry run, Stages A–E, the secondary cells, and the negative
control:

- Python 3.14.3 (CPython, macOS arm64)
- numpy 2.5.2
- scipy 1.18.1
- pytest 9.1.1 (iniconfig 2.3.0, packaging 26.3, pluggy 1.6.0, Pygments 2.21.0)

## Civil Comments additional audit

Design-stage freeze artifacts (`scripts/civil_comments_freeze.py`) were
produced in a recreated project virtualenv (`.venv`, editable install):

- Python 3.14.3 (CPython, macOS arm64)
- numpy 2.5.2, scipy 1.18.1, pandas 3.0.5, pytest 9.1.1

The pinned Detoxify scoring environment (`.venv-cc`, uv-created; frozen
in `config/civil_comments_additional_audit.json` before any scoring):

- Python 3.12.11 (CPython, macOS arm64)
- detoxify 0.5.2, torch 2.13.0, transformers 5.16.1, tokenizers 0.23.1,
  sentencepiece 0.2.2, safetensors 0.8.0, huggingface-hub 1.28.0,
  numpy 2.5.2

## Post hoc robustness package (scripts/posthoc_*.py)

Run under the system interpreter (Homebrew CPython) rather than the venv:

- Python 3.14.3
- pandas 3.0.2
- numpy 2.4.4
- scipy 1.17.1

The differing numpy and scipy versions are inert for these scripts. The
test framework (`offcriterion.permutation`) is pure numpy with explicitly
seeded `SeedSequence` generators, and the Stage 3 and Stage 4 post hoc
reruns of the Z0 statistics reproduced the frozen confirmatory values
exactly (see `results/posthoc/robustness_tests.json` vs
`results/*_analysis.json`).
