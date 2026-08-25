# OffCriterion

**Does an LLM evaluator's score retain information about a prespecified
off-criterion attribute after conditioning on the observed target construct?**

This repository validates a statistical method for that question on **synthetic
data only**. No real dataset, model, or API is touched anywhere in the code.

---

## The question

An evaluator assigns a score `S`. We have a prespecified attribute `A` that the
rubric says should be irrelevant -- an off-criterion attribute. We also observe
`Z`, a discrete representation of the intended construct the evaluator is
supposed to be scoring.

The concern is not that `S` and `A` are correlated. They usually will be, because
both depend on genuine quality. The concern is whether `S` still carries
information about `A` **once the observed construct is accounted for**.

## The null hypothesis

```
H0 :  S  _||_  A  |  Z
```

`S` is conditionally independent of `A` given `Z`. Rejecting `H0` says the score
carries information about the off-criterion attribute beyond what the observed
construct explains.

## The test

A **stratified permutation test**. The auditor holds `S` and `Z` fixed and
permutes `A` only within sets of units sharing an *identical* value of `Z`. This
preserves the attribute counts inside every stratum exactly, and nothing ever
moves across a stratum boundary.

Under i.i.d. sampling and `H0`, the within-stratum permutation distribution is
the exact conditional null distribution of any statistic -- finite-sample exact,
with no asymptotics and no assumption on the shape of `P(S | Z)`. The argument,
and the four assumptions it depends on, are in
[`docs/assumptions.md`](docs/assumptions.md).

The implementation is a **Monte Carlo (random) permutation test**: it draws
`B` within-stratum permutations uniformly at random rather than enumerating
the full permutation group. The p-value is

```
p = (1 + #{ b : T_b >= T_obs }) / (B + 1)
```

which is bounded below by `1/(B+1)` and therefore never zero. Because the
observed arrangement and the `B` draws are exchangeable under `H0`, this
random-permutation construction is itself finite-sample valid for any `B`;
exhaustive enumeration is not required for validity, only for removing the
Monte Carlo component of the p-value.

### The statistic

The default is the conditional likelihood-ratio statistic on the contingency
table of `(S, A, Z)`:

```
G^2 = 2 sum_{z,s,a} n_{zsa} log( n_{zsa} n_z / (n_{zs} n_{za}) )  =  2 n * I_hat(S ; A | Z)
```

It compares the full three-way table against the conditional-independence model,
so it responds to differences in location, scale, skewness, tail mass or
modality alike -- it does not privilege the mean. Its limitation is stated
precisely rather than glossed: it is omnibus **with respect to the score
discretisation**, and conditional laws that induce identical bin probabilities
are invisible to it at any sample size.

The 8 pooled quantile bins used below are a choice for the *continuous
synthetic scores* only. A real experiment whose judge emits an ordinal rubric
score (e.g. a 1-6 holistic scale) should use the native score categories
directly, with no discretisation step, unless there is a documented statistical
reason not to.

Statistics live in a registry (`offcriterion.statistics.STATISTICS`) and are
interchangeable. Validity holds for any of them -- the permutation argument never
mentions the statistic -- so the choice affects power only.

---

## Results

`alpha = 0.05`, 1000 replicates per cell, `B = 999` permutations, 8 pooled
quantile score bins. Brackets are Wilson 95% intervals; the Monte Carlo standard
error on a rate near 0.05 is about 0.007.

**Every column below is calibrated by the same within-stratum permutation
scheme**, so differences between them are attributable to the statistic rather
than to how its reference distribution was obtained. (The marginal t-test is the
deliberate exception -- see the note under the table.)

### Rejection rates at n = 2000

| Scenario | Null | Proposed (cond. G²) | Mean disparity | Regression LRT | Marginal t-test\* |
|---|---|---|---|---|---|
| `conditional_null` | H0 true | 0.046 [0.035, 0.061] | 0.056 [0.043, 0.072] | 0.055 [0.042, 0.071] | 1.000 |
| `mean_dependence` | H0 false | 0.907 [0.887, 0.923] | 0.998 [0.993, 0.999] | 0.999 [0.994, 1.000] | 1.000 |
| `variance_only` | H0 false | **1.000** [0.996, 1.000] | 0.048 [0.036, 0.063] | 0.044 [0.033, 0.059] | 1.000 |
| `shape_only` | H0 false | **0.705** [0.676, 0.732] | 0.044 [0.033, 0.059] | 0.051 [0.039, 0.066] | 1.000 |
| `confounded_observed` | H0 true | 0.048 [0.036, 0.063] | 0.051 [0.039, 0.066] | 0.046 [0.035, 0.061] | 1.000 |
| `confounded_proxy` | H0 not guaranteed | 0.991 [0.983, 0.995] | 1.000 [0.996, 1.000] | 1.000 [0.996, 1.000] | 1.000 |

\* The marginal t-test conditions on nothing, so it tests `S _||_ A`, **not** the
audit null. Its rejections in the two conditional-null rows are correct answers
to a different question, not Type I errors. It is shown to make the cost of
skipping the conditioning step visible: aggregate disparity is overwhelming in
every scenario here, including the ones where the score is conditionally clean.

### Calibration versus power, by sample size

Proposed statistic (conditional G²):

| Scenario | n = 200 | n = 500 | n = 2000 |
|---|---|---|---|
| `conditional_null` | 0.056 | 0.049 | 0.046 |
| `mean_dependence` | 0.142 | 0.254 | 0.907 |
| `variance_only` | 0.285 | 0.788 | 1.000 |
| `shape_only` | 0.095 | 0.162 | 0.705 |
| `confounded_observed` | 0.037 | 0.035 | 0.048 |
| `confounded_proxy` | 0.189 | 0.425 | 0.991 |

Mean disparity baseline (same permutation null):

| Scenario | n = 200 | n = 500 | n = 2000 |
|---|---|---|---|
| `conditional_null` | 0.053 | 0.042 | 0.056 |
| `mean_dependence` | 0.224 | 0.566 | 0.998 |
| `variance_only` | 0.050 | 0.048 | 0.048 |
| `shape_only` | 0.047 | 0.046 | 0.044 |
| `confounded_observed` | 0.047 | 0.037 | 0.051 |
| `confounded_proxy` | 0.393 | 0.837 | 1.000 |

Full tables, including the regression baselines, are in `results/results.md` and
`results/results.tex`; raw per-replicate p-values are in `results/replicates.csv`.

### What the numbers say

- **Calibration holds.** Both true-null scenarios sit at nominal at every sample
  size, including `confounded_observed`, where `A -> Q -> S` makes the marginal
  disparity overwhelming (`marginal t-test = 1.000`) while the conditional test
  stays at 0.035-0.051.
- **Aggregate disparity is blind to non-mean dependence.** In `variance_only` and
  `shape_only` the conditional score distributions differ genuinely, and both
  mean-oriented baselines stay flat at nominal across a tenfold increase in
  sample size -- they are not underpowered, they are *inconsistent* against these
  alternatives. The table statistic reaches 1.000 and 0.705 respectively.
- **Omnibus power is not free.** Under `mean_dependence` the mean baselines beat
  the table statistic (0.998 vs 0.907), which is exactly as expected: a
  correctly-specified one-degree-of-freedom test should win against the
  alternative it was designed for. The argument for the proposed test is
  robustness across the shape of the departure, not uniform superiority.
- **Imperfect measurement of the construct produces residual dependence.** In
  `confounded_proxy` the null is *false* by construction, and the high rejection
  rates are correct rejections. Because the coarsening-induced dependence is
  largely a mean shift, the mean baselines detect it sooner than the omnibus
  statistic (0.393 vs 0.189 at n=200) -- a reminder that these rows measure the
  cost of a weaker conditioning set, not a property of the test.

**These results do not establish finite-sample validity.** Exactness is a
mathematical consequence of the assumptions in
[`docs/assumptions.md`](docs/assumptions.md); the simulations are evidence that
this *implementation* matches that mathematics on data satisfying them. The
distinction is maintained deliberately throughout the code comments and docs.

---

## The six scenarios

| Scenario | Generative process | Null status |
|---|---|---|
| `conditional_null` | `S = mu(Q) + e`, `A \| Q ~ Bernoulli(sigmoid(.))` | **true** |
| `mean_dependence` | adds `+0.30 * A` to the conditional mean | false |
| `variance_only` | equal conditional means, sd 1.0 vs 1.6 | false |
| `shape_only` | matched conditional mean, variance **and** skewness; excess kurtosis 0 vs ~1.7 | false |
| `confounded_observed` | `A -> Q -> S`, conditioning on the exact `Q` | **true** |
| `confounded_proxy` | `A -> Q -> S`, conditioning on discretised `Y = Q + noise` | **not guaranteed** |

In scenarios 1-4 the attribute depends on `Q`. That is deliberate: if `A` were
independent of `Q`, conditioning would be vacuous and the scenarios would not
test anything about *conditional* independence. It also means `S` and `A` are
strongly dependent marginally in all of them, including the null one.

`shape_only` is the sharpest case, and its "matched through three moments" claim
is verified rather than asserted -- `tests/test_scenarios.py` checks the
conditional mean, variance and skewness agree across `A` in every stratum while
the fourth moment separates them.

A scenario whose signal vanished under the chosen binning would make low power
look like a finding when it was an artifact. `offcriterion diagnostics` therefore
reports the population `I(S_binned ; A | Z)` each scenario induces at the binning
actually used, against the plug-in estimator's own bias floor:

| Scenario | population `I(S_bin; A \| Z)` | detectable at 8 bins |
|---|---|---|
| `conditional_null` | 0.000075 | no (at the bias floor, as it must be) |
| `mean_dependence` | 0.007964 | yes |
| `variance_only` | 0.027965 | yes |
| `shape_only` | 0.005639 | yes |
| `confounded_observed` | 0.000037 | no (at the bias floor, as it must be) |
| `confounded_proxy` | 0.013315 | yes |

---

## Reproducing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

offcriterion run                 # the full experiment; ~1 minute on 14 cores
```

That single command runs the design diagnostics, all 18,000 replicate fits, and
writes every artifact below. Results are deterministic: seeds are derived from
the root seed and each replicate's *position* via `SeedSequence` spawn keys, so
output is identical regardless of worker count or completion order.

```bash
offcriterion run --quick         # 100 replicates, B=199 -- smoke configuration
offcriterion diagnostics         # population CMI and conditional moments only
offcriterion tables              # re-render tables from saved results
offcriterion run --help          # alpha, bins, binning strategy, sizes, seed, workers
```

### Output

| File | Contents |
|---|---|
| `results/replicates.csv` | every replicate's p-value, long format |
| `results/rejection_rates.csv` / `.json` | rejection rates with Wilson intervals |
| `results/results.md` / `.tex` | publication-ready tables |
| `results/diagnostics.json` | population CMI and conditional moments per scenario |
| `results/config.json` | the exact configuration, including the root seed |

### Tests

```bash
pytest                      # full suite
pytest -m "not slow"        # skip the Monte Carlo calibration tests
```

The suite is deliberately adversarial about the properties that validity depends
on:

- **Permutation never crosses strata**, and stratum attribute counts are
  preserved exactly (checked over hundreds of draws, with a label-per-stratum
  construction that would make any leak visible).
- **The permutation draw is uniform** over the within-stratum symmetric group
  (all `3!` arrangements enumerated, chi-square against the 0.999 quantile).
- **Exactness of the machinery** by exhaustive enumeration: on a problem small
  enough to enumerate every within-stratum permutation, the Monte Carlo p-value
  is checked against the exact one.
- **Statistics pinned to closed forms** on hand-constructed tables -- `G² = 0` on
  a product table, `G² = 2n log 2` under perfect dependence, mean disparity
  `= 1.0`, regression LRT `= 4 log 5` -- plus a miniature case where a scale
  difference gives both mean statistics exactly zero and the table statistic a
  positive value.
- **Fast path against a naive oracle**: every statistic's cached implementation
  is compared to a from-scratch recomputation over many valid permutations.
- **The p-value is always in (0, 1]**, equals `(1 + k)/(B + 1)`, and is bounded
  below by `1/(B+1)`; near-ties resolve conservatively.
- **Identical seeds reproduce identical results**, including across worker
  counts, and different seeds do not.
- **No binning function can see the attribute** -- enforced by signature
  inspection, so an A-dependent preprocessing step cannot be introduced quietly.
- **Type I error under two known nulls** is at or below nominal, and null
  p-values are super-uniform at `alpha` in {0.01, 0.05, 0.10, 0.20} -- not only at
  the headline level.
- **Scenarios generate what they claim**, verified through the first four
  conditional moments.

---

## Layout

```
src/offcriterion/
  data.py          RawSample / Sample containers, stratum index
  discretize.py    A-free score binning (structurally cannot see the attribute)
  statistics.py    statistic registry: conditional G^2 / CMI, mean and regression baselines
  permutation.py   within-stratum permutation, Monte Carlo p-value
  scenarios.py     the six synthetic generative processes
  baselines.py     non-permutation baselines (marginal t-test, asymptotic F)
  diagnostics.py   population CMI and conditional moments per scenario
  experiment.py    replicate loop, seeding, parallelism, aggregation
  tables.py        publication-ready markdown and LaTeX
  storage.py       CSV / JSON persistence
  cli.py           `offcriterion run | diagnostics | tables`
docs/assumptions.md   assumptions, guarantees, and what the simulations do not show
```

Dependencies are `numpy` and `scipy` only (`scipy` for distribution functions in
the asymptotic baselines and the Wilson interval); `pytest` for the test suite.
No dataframe library -- results are plain CSV and JSON.

## Status and scope

Prototype, synthetic validation only. `Z` must be discrete so that permutation
can be exact within identical strata. Known gaps before this could touch real
evaluator data -- clustered observations, continuous `Z`, multiplicity across
attributes -- are listed in
[`docs/assumptions.md`](docs/assumptions.md#4-known-open-issues-for-a-real-data-version).
