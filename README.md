# Automated Evaluator Audit

Code, preregistration, and frozen artifacts for the paper
**"What Else Do Automated Evaluators Measure?"**

> Naming note: the Python package, CLI, and historical documents in this
> repository use the project's original internal name, **`offcriterion`**.
> That name is retained deliberately — file hashes, a preregistration, and
> frozen analysis records reference it — and `offcriterion` remains a working
> command. `evaluator-audit` is an equivalent alias. Historical documents
> that say "OffCriterion" are frozen records and have not been edited.

## The question

An automated (LLM) evaluator assigns a score `S` to a piece of work. A
prespecified attribute `A` — one the rubric says should be irrelevant — is
also observed, along with `Z`, a discrete representation of the construct the
evaluator is supposed to measure. `S` and `A` are usually correlated, because
both track genuine quality. The audit asks a sharper question: does `S`
still carry information about `A` **after conditioning on the observed
construct**?

```
H0 :  S  ⫫  A  |  Z   (S independent of A given Z)
```

The test is a **stratified permutation test**: hold `S` and `Z` fixed and
permute `A` only within sets of units sharing an identical `Z`. Two
properties matter and are deliberately separated:

- **Conditional calibration** comes from the stratified randomization. Under
  i.i.d. sampling and `H0`, within-stratum permutation is the *exact*
  conditional null distribution of any statistic — finite-sample, no
  asymptotics, no model for `P(S | Z)` (`docs/assumptions.md`).
- **Sensitivity beyond mean differences** comes from the statistic: the
  conditional likelihood-ratio `G²` on the `(S, A, Z)` table responds to
  differences in location, spread, or shape of the conditional score
  distributions, where mean-based disparity statistics are provably blind to
  non-mean departures.

## What is in this repository

**1. Synthetic validation** (`src/offcriterion/`, no APIs, no real data).
Six generative scenarios with known truth show the test holds its nominal
size under two true nulls and detects variance-only (power 1.000 at
n = 2000) and shape-only (0.705) departures that mean-based baselines miss
entirely (~0.05). Full tables: `results/results.md`.

**2. A preregistered real-data case study** on PERSUADE 2.0 (25,996 student
argumentative essays with human holistic scores and demographic metadata).
`S` = LLM judge holistic score (1–6), `A` = writer ELL (English language
learner) status, `Z` = (writing prompt, human holistic score). A census of
the 11,360 usable Independent-writing essays was scored by three evaluator
families under pinned model snapshots:

| Evaluator | Condition | Status |
|---|---|---|
| GPT-5.4-mini | plain rubric | preregistered primary |
| Claude Haiku 4.5 | plain rubric | secondary confirmatory (Holm) |
| Gemini 3.7 Flash | plain rubric | secondary confirmatory (Holm) |
| GPT-5.4-mini | "ignore demographics" rubric | secondary confirmatory (Holm) |

All four cells reject the conditional-independence null (Monte Carlo
p = 0.001, the smallest attainable at B = 999; Holm-adjusted p = 0.003 for
the secondary family). Conditional mean gaps (ELL − non-ELL, matched on
prompt and human score) range from −0.32 to −0.60 rubric points.

**3. A frozen post-hoc robustness package** (labeled as such, never
confirmatory): richer human-quality and length adjustment attenuates the
gaps by at most ~11% with all tests still at p = 0.001; a paired analysis
shows the "ignore demographics" instruction did **not** mitigate the
conditional gap (attenuation −0.057, 95% CI [−0.093, −0.014]); and
judge-vs-human alignment metrics show the evaluators do track the rubric
(QWK 0.56–0.74) while exhibiting the residual dependence.

### Interpretation limits

Rejection establishes **residual conditional statistical dependence** —
nothing more. It is not proof of causal use of demographic information, of
discrimination, or of unfairness: the human score is an imperfect proxy for
the intended construct, and ELL-correlated linguistic features may be
construct-relevant under a writing rubric. See §18 of
`docs/preregistration.md` and part C of `docs/junior_spotlight_evidence.md`.

## Preregistered vs post-hoc

| Evidence | Where |
|---|---|
| Preregistration (frozen before any scoring) | `docs/preregistration.md`, `config/preregistered.json` |
| Frozen judge prompts | `prompts/` |
| Frozen sample census + artifact hashes | `data/scoring/stage_a_freeze.json`, `primary_sample_manifest.csv` |
| Raw evaluator outputs, checksum-frozen | `data/scoring/*/` (`FROZEN.json` manifests) |
| Confirmatory analyses | `results/primary_analysis.json`, `results/secondary_*`, `results/negative_control.json` |
| Deviations (all disclosed) | `docs/deviations.md` |
| Post-hoc plan (committed before execution) | `docs/posthoc_robustness_plan.md` |
| Post-hoc results | `results/posthoc/`, `results/posthoc_exclusion_audit.md` |
| Evidence hierarchy for the paper | `docs/junior_spotlight_evidence.md` |

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,analysis]"     # analysis = pandas, used by post-hoc scripts
```

`evaluator-audit` and `offcriterion` are the same CLI.

## Reproducing

**No API calls or paid scoring are required to reproduce any reported
number.** Every evaluator output is frozen in `data/scoring/` with SHA-256
manifests; all statistical analyses re-run locally and deterministically
from those frozen scores. The only scripts that contact external APIs are
`scripts/run_primary_scoring.py` and `scripts/run_secondary_scoring.py` —
do not run them unless you intend to pay for a new scoring run.

```bash
# 1. Synthetic validation (~1 minute, fully self-contained)
evaluator-audit run

# 2. Real-data inputs: download PERSUADE 2.0 (see data/persuade/README.md
#    for canonical sources + SHA-256), then rebuild the derived inputs:
python scripts/prepare_persuade.py --out-dir data/persuade
#    (verifies byte-exact SHA-256 reproduction of all three derived files)

# 3. Re-run any analysis from the frozen scores, e.g.:
python scripts/stage_e_analysis.py        # preregistered primary analysis
python scripts/negative_control.py        # preregistered negative control
python scripts/holm_secondary_family.py   # Holm family summary
python scripts/posthoc_robustness_tests.py  # post-hoc Z0/Z1/Z2 tests
```

The complete stage-by-stage map — every script, its inputs/outputs, its
frozen/preregistered/post-hoc status, and whether it touches an external
API — is in **`docs/REPRODUCING.md`** (see also `scripts/README.md`).

## Repository layout

```
src/offcriterion/        core test + synthetic study + scoring/analysis pipeline
scripts/                 stage scripts, chronological (index: scripts/README.md)
tests/                   adversarial suite for the properties validity depends on
config/preregistered.json  frozen machine-readable preregistration
prompts/                 frozen judge prompt templates
docs/                    preregistration, assumptions, deviations, plans, guides
data/persuade/           corpus (not redistributed; README has provenance + hashes)
data/scoring/            frozen raw evaluator outputs (checksum manifests)
results/                 synthetic tables, confirmatory analyses, post-hoc package
```

## Data and licensing

- **Repository code**: MIT (`LICENSE`).
- **PERSUADE 2.0 corpus**: CC BY-NC-SA 4.0; **not redistributed here** —
  `data/persuade/README.md` documents how to obtain it and the SHA-256 of
  the canonical files. Tracked corpus-derived artifacts (essay-ID manifests,
  per-essay quality indices) remain subject to the corpus terms.
- **Evaluator outputs**: raw provider responses are published as research
  evidence, not relicensed as original code.

Details: `DATA_LICENSES.md`.
