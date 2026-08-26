# Automated Evaluator Audit

Code, preregistration, and frozen artifacts for the paper
**"What Else Do Automated Evaluators Measure?"**

> A note on names. The repository is called Automated Evaluator Audit. The
> Python package and CLI keep the project's original internal name,
> `offcriterion`, because the preregistration, file hashes, and frozen
> analysis records reference it. `evaluator-audit` and `offcriterion` run
> the same CLI. Historical documents that say "OffCriterion" are frozen
> records and have not been edited.

## The question

An automated evaluator assigns a score `S` to a piece of work. Alongside
`S`, the audit observes `A`, a prespecified external attribute that is not
itself part of the scoring target, and `Z`, a discrete representation of
the construct the evaluator is supposed to measure. `S` and `A` are
usually correlated, because both track genuine quality. The audit asks
whether `S` still carries information about `A` after conditioning on the
observed construct.

```
H0 :  S  ⫫  A  |  Z   (S independent of A given Z)
```

The test holds `S` and `Z` fixed and permutes `A` within sets of units
that share an identical `Z`. Two properties matter, and they come from
different parts of the design.

- **Conditional calibration** comes from the randomization scheme. Under
  i.i.d. sampling and `H0`, observations within a stratum are
  exchangeable, so stratified permutation gives finite sample valid
  randomization inference with no asymptotics and no model for `P(S | Z)`
  (`docs/assumptions.md`). The implementation is Monte Carlo, with
  B = 999 random permutations per test.
- **Sensitivity beyond mean differences** comes from the statistic. The
  conditional likelihood ratio `G²` on the `(S, A, Z)` table responds to
  changes in the location, spread, or shape of the conditional score
  distributions. A statistic based only on the conditional mean cannot
  detect an alternative that leaves that mean unchanged. The variance
  only and shape only scenarios in the synthetic study are exactly such
  alternatives.

## What is in this repository

**1. Synthetic validation** (`src/offcriterion/`, no APIs, no real data).
In six generative scenarios with known truth, the test holds its nominal
size under both true nulls and detects the variance only departure
(power 1.000 at n = 2000) and the shape only departure (0.705). The
stratified mean disparity baseline rejects those same alternatives at
0.048 and 0.044, indistinguishable from its false positive rate. Full
tables are in `results/results.md`.

**2. A preregistered real data case study** on PERSUADE 2.0 (25,996
student argumentative essays with human holistic scores and demographic
metadata). Here `S` is the evaluator's holistic score on the 1 to 6
rubric scale, `A` is the writer's English language learner (ELL) status,
and `Z` is the pair (writing prompt, human holistic score). A census of
the 11,360 usable Independent writing essays was scored by three
evaluator families under pinned model snapshots, in two prompt
conditions. The standard prompt is the frozen scoring prompt in
`prompts/`. The modified prompt adds one instruction telling the
evaluator not to infer or use demographic characteristics of the writer.
Demographic metadata was withheld from the evaluators in both conditions.

| Evaluator | Prompt | Status |
|---|---|---|
| GPT-5.4-mini | standard | preregistered primary |
| Claude Haiku 4.5 | standard | secondary confirmatory (Holm) |
| Gemini 3.7 Flash | standard | secondary confirmatory (Holm) |
| GPT-5.4-mini | modified | secondary confirmatory (Holm) |

All four cells reject the conditional independence null at Monte Carlo
p = 0.001, the smallest value attainable at B = 999. The Holm adjusted
p value for the secondary family is 0.003. Conditional mean gaps
(ELL − non-ELL, matched on prompt and human score) range from −0.32 to
−0.60 rubric points.

**3. A post hoc robustness package** whose plan was frozen and committed
before execution. These analyses are labeled post hoc throughout and are
never treated as confirmatory. Adjusting for a richer human quality index
and essay length attenuates the conditional gaps by at most 10.9%, with
every test still at p = 0.001. A paired analysis shows the modified
prompt did not mitigate the conditional gap (attenuation −0.057, 95% CI
[−0.093, −0.014]). Alignment metrics show the evaluators do track the
rubric (quadratic weighted kappa 0.56 to 0.74) while exhibiting the
residual dependence.

### Interpretation limits

Rejection establishes residual conditional statistical dependence, and
nothing beyond that. It is not evidence of causal use of demographic
information, of discrimination, or of unfairness. The human score is an
imperfect proxy for the intended construct, and linguistic features
correlated with ELL status may be relevant to a writing rubric. See §18
of `docs/preregistration.md` and part C of
`docs/junior_spotlight_evidence.md`.

## Preregistered vs post hoc

| Evidence | Where |
|---|---|
| Preregistration (frozen before any scoring) | `docs/preregistration.md`, `config/preregistered.json` |
| Frozen evaluator prompts | `prompts/` |
| Frozen sample census + artifact hashes | `data/scoring/stage_a_freeze.json`, `primary_sample_manifest.csv` |
| Raw evaluator outputs with checksum manifests | `data/scoring/*/` (`FROZEN.json`) |
| Confirmatory analyses | `results/primary_analysis.json`, `results/secondary_*`, `results/negative_control.json` |
| Deviations (all disclosed) | `docs/deviations.md` |
| Post hoc plan (committed before execution) | `docs/posthoc_robustness_plan.md` |
| Post hoc results | `results/posthoc/`, `results/posthoc_exclusion_audit.md` |
| Evidence hierarchy for the paper | `docs/junior_spotlight_evidence.md` |

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,analysis]"     # analysis = pandas, used by the post hoc scripts
```

`evaluator-audit` and `offcriterion` are the same CLI.

## Reproducing

No API calls or paid scoring are required to reproduce any reported
number. Every evaluator output is frozen in `data/scoring/` with SHA-256
manifests, and all statistical analyses re-run locally and
deterministically from those frozen scores. The only scripts that contact
external APIs are `scripts/run_primary_scoring.py` and
`scripts/run_secondary_scoring.py`. Do not run them unless you intend to
pay for a new scoring run.

```bash
# 1. Synthetic validation (~1 minute, fully self-contained)
evaluator-audit run

# 2. Real data inputs: download PERSUADE 2.0 (see data/persuade/README.md
#    for canonical sources and SHA-256), then rebuild the derived inputs:
python scripts/prepare_persuade.py --out-dir data/persuade
#    (verifies byte exact SHA-256 reproduction of all three derived files)

# 3. Re-run any analysis from the frozen scores, e.g.:
python scripts/stage_e_analysis.py        # preregistered primary analysis
python scripts/negative_control.py        # preregistered negative control
python scripts/holm_secondary_family.py   # Holm family summary
python scripts/posthoc_robustness_tests.py  # post hoc Z0/Z1/Z2 tests
```

`docs/REPRODUCING.md` maps every stage in order, with each script's
inputs and outputs, its evidentiary status, and whether it touches an
external API. `scripts/README.md` indexes the scripts by stage.

## Repository layout

```
src/offcriterion/        core test + synthetic study + scoring/analysis pipeline
scripts/                 stage scripts, chronological (index: scripts/README.md)
tests/                   adversarial suite for the properties validity depends on
config/preregistered.json  frozen machine readable preregistration
prompts/                 frozen evaluator prompt templates
docs/                    preregistration, assumptions, deviations, plans, guides
data/persuade/           corpus (not redistributed, README has provenance and hashes)
data/scoring/            frozen raw evaluator outputs (checksum manifests)
results/                 synthetic tables, confirmatory analyses, post hoc package
```

## Data and licensing

- **Repository code** is MIT licensed (`LICENSE`).
- **PERSUADE 2.0 corpus** is CC BY-NC-SA 4.0 and is not redistributed
  here. `data/persuade/README.md` documents how to obtain it and the
  SHA-256 of the canonical files. Tracked artifacts derived from the
  corpus (sample manifests and quality indices keyed by essay ID) remain
  subject to the corpus terms.
- **Evaluator outputs** are raw provider responses, published as research
  evidence rather than relicensed as original code.

Details are in `DATA_LICENSES.md`.
