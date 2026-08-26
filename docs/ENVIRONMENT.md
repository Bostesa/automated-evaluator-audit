# Environments that produced the reported results

Exact historical environments are recorded for the audit trail; the code is
not believed to require them (dependencies are declared with loose lower
bounds in `pyproject.toml`, and results are seed-deterministic).

## Synthetic validation, scoring pipeline, and confirmatory analyses

Project virtualenv (`.venv`, editable install), used for the synthetic study,
the dry run, Stage A–E, the secondary cells, and the negative control:

- Python 3.14.3 (CPython, macOS arm64)
- numpy 2.5.2
- scipy 1.18.1
- pytest 9.1.1 (iniconfig 2.3.0, packaging 26.3, pluggy 1.6.0, Pygments 2.21.0)

## Post-hoc robustness package (scripts/posthoc_*.py)

Run under the system interpreter (Homebrew CPython) rather than the venv:

- Python 3.14.3
- pandas 3.0.2
- numpy 2.4.4
- scipy 1.17.1

The differing numpy/scipy versions are inert for these scripts: the frozen
test framework (`offcriterion.permutation`) is pure numpy with explicitly
seeded `SeedSequence` generators, and the Stage-3/4 post-hoc reruns of the
Z0 statistics reproduced the frozen confirmatory values exactly (see
`results/posthoc/robustness_tests.json` vs `results/*_analysis.json`).
