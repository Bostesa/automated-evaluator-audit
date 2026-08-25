# Assumptions, guarantees, and what the simulations do and do not show

This document exists to keep two things apart that are easy to conflate:

1. what follows **mathematically** from the assumptions of the stratified
   permutation test, and
2. what the synthetic experiments in this repository provide **empirical**
   evidence for.

The simulations are evidence that the implementation matches the mathematics.
They are not, and cannot be, a demonstration that the test is valid. A test can
pass every simulation here and still be invalid on data that violates the
assumptions below.

---

## 1. The mathematical claim

**Setting.** We observe `n` units, each carrying a score `S`, a prespecified
off-criterion attribute `A`, and a discrete conditioning variable `Z`
representing the observed intended construct.

**Null hypothesis.**

```
H0 :  S  _||_  A  |  Z
```

**Procedure.** Hold `S` and `Z` fixed. Permute `A` uniformly at random within
each set of units sharing an identical value of `Z`, independently across those
sets. Recompute the statistic. Report

```
p = (1 + #{ b : T_b >= T_obs }) / (B + 1)
```

**Claim.** Under assumptions A1-A4 below, this test is *exact*: for any
significance level `alpha` of the form `k/(B+1)`,

```
P(p <= alpha | H0)  <=  alpha
```

with equality in the absence of ties in the statistic.

### Proof sketch

Condition on the whole data except the attribute labels. Under i.i.d. sampling
from `P(S, A, Z)`,

```
P(A_1..A_n | S_1..S_n, Z_1..Z_n)  =  prod_i P(A_i | S_i, Z_i)
```

and under `H0` each factor reduces to `P(A_i | Z_i)`. That second equality *is*
the null hypothesis; nothing else is used. Inside a stratum `{i : Z_i = z}` every
factor is the same law `P(A | Z = z)`, so the labels there are exchangeable.
Strata are conditionally independent, so the joint conditional law of the labels
is exchangeable within strata and independent across them. Conditioning further
on the observed multiset of labels in each stratum, every within-stratum
arrangement is equally likely. Hence the within-stratum permutation distribution
*is* the exact conditional null distribution of any statistic, and the Monte
Carlo p-value above is the standard exact Monte Carlo test over `B + 1`
exchangeable draws.

### A1. Units are i.i.d., or at least exchangeable within strata

The factorisation step requires it. **This is the assumption most likely to fail
on real evaluator data**, and it fails silently. Multiple items generated from
one prompt, repeated evaluator calls on one item, items sharing an author or a
source document, or any temporal drift in the evaluator all induce dependence
between units in the same stratum. Under clustering the permutation
distribution is too narrow and the test is anti-conservative -- it rejects too
often, which for an audit is the dangerous direction.

There is no diagnostic in this repository for A1. It has to be argued from how
the data was collected, and if it fails the remedy is to permute whole clusters,
not units.

### A2. `Z` is observed exactly and matched exactly

The exchangeability step needs every unit in a stratum to share the *same*
`P(A | Z = z)`, which follows from their sharing the same value of `Z`.
Approximate matching does not suffice. Coarsening `Z` -- binning a continuous
construct, or conditioning on a noisy proxy -- changes the null being tested from
`S _||_ A | Q` to `S _||_ A | coarsen(Q)`, and the second does not follow from
the first.

This is exactly what the `confounded_proxy` scenario demonstrates. Its
rejections are **correct rejections of a false null**, not Type I errors. The
test remains exact for the null it actually states; it is the stated null that
has changed. Reporting that scenario as "the permutation test loses validity
under measurement error" would be wrong.

The practical consequence for an auditor: the guarantee is always relative to the
conditioning set you actually used, and a construct measured with error yields a
weaker guarantee than the one you probably wanted.

### A3. Nothing in the pipeline depends on `A`

Any preprocessing that is a function of `(S, Z)` alone is safe, because the
permutation holds `S` and `Z` fixed and such a transform is therefore constant
across the entire permutation distribution. Pooled sample quantile bins of `S`
qualify, *even though they are data-dependent*.

Anything that touches `A` does not qualify -- attribute-stratified bin edges,
filtering on attribute-conditional statistics, choosing the number of bins by
looking at the result. Such a step breaks exactness while leaving the simulation
output looking entirely normal, which is why the rule is enforced structurally:
every function in `offcriterion.discretize` is written to be incapable of
accepting an attribute argument, and `tests/test_discretize.py` asserts that by
inspecting the signatures.

### A4. Permutations are drawn uniformly and independently

`B` draws i.i.d. uniform from the product of the within-stratum symmetric groups.
Verified by direct enumeration in `tests/test_permutation.py`.

---

## 2. What the choice of statistic does and does not affect

Validity holds for **any** statistic; the proof never mentions one. The statistic
determines power only. This is what makes the statistic registry safe to extend.

The default statistic is the conditional likelihood-ratio statistic

```
G^2 = 2 sum_{z,s,a} n_{zsa} log( n_{zsa} n_z / (n_{zs} n_{za} ) )  =  2 n * I_hat(S ; A | Z)
```

which compares the full three-way table against the conditional-independence
model and therefore responds to differences in location, scale, skew, tail mass
or modality alike.

**The limitation, stated precisely.** It is omnibus *with respect to the score
discretisation*, not in general. Two conditional laws that induce identical bin
probabilities are indistinguishable to it, at any sample size. "Sensitive to
general distributional dependence" means "consistent against alternatives that
survive the binning", and nothing stronger.

Because this limitation could easily be mistaken for a finding, the repository
reports the population quantity `I(S_binned ; A | Z)` induced by each scenario at
the binning actually used (`offcriterion diagnostics`). If a scenario shows low
power *and* near-zero population signal, the correct conclusion is that the
experiment was badly specified, not that the statistic is weak.

### Sparse tables

The plug-in `G^2` is biased upward when cells are sparse. This does **not**
threaten validity: every permuted table has the same `n_zs`, `n_za` and `n_z`
margins as the observed one, so the same bias is present throughout the
reference distribution and cancels in the comparison. It does cost power.

### Ties and conservativeness

On sparse tables `G^2` takes many repeated values, so exact ties in the
permutation distribution are common. With the `>=` convention the test is valid
but conservative, and the empirically observed Type I error sits slightly below
`alpha` -- around 0.043 at `alpha = 0.05` in the runs reported here. That is the
expected behaviour of a valid discrete test, not a defect, and it is not
"corrected" by randomised tie-breaking anywhere in this code.

Near-ties are additionally resolved *towards* counting, using a relative
tolerance, so that floating-point noise can only move the p-value in the
conservative direction.

### Strata that cannot contribute

A stratum with fewer than two units, or with a constant attribute, admits only
the identity permutation. It contributes an identical constant to the observed
statistic and to every permuted one, so it cancels: harmless for validity, dead
weight for power. Every result record reports `n_usable_strata` alongside
`n_strata` so that a table full of unusable strata is visible rather than
inferred.

---

## 3. What the simulations establish

They establish that **the implementation behaves the way the mathematics says it
should**, on data that satisfies the assumptions. Specifically:

- Under two different true conditional nulls, the empirical rejection rate is at
  or slightly below nominal at every sample size tested.
- The null p-value distribution is super-uniform at several levels, not only at
  0.05 -- a test calibrated at one level only would pass a single headline check
  while being wrong elsewhere.
- Power rises with sample size and effect size under mean dependence.
- Under variance-only and shape-only alternatives, both mean-oriented statistics
  stay at nominal while the table statistic gains power.

They establish none of the following, and the README does not claim them:

- that the test is valid on data with clustered or otherwise non-exchangeable
  units (A1 is assumed, never tested);
- that the test is valid for continuous or high-cardinality `Z` (out of scope for
  this prototype; exact matching would fail);
- that the finite-sample guarantee holds at sample sizes, stratum counts or
  effect sizes outside the grid that was actually run;
- that the statistic is omnibus against alternatives invisible at the binning;
- anything at all about real evaluator scores. Every number in this repository
  comes from a synthetic generative process defined in
  `src/offcriterion/scenarios.py`.

---

## 4. Known open issues for a real-data version

- **Clustering (A1).** Needs a cluster-permutation variant before any real
  evaluator data is used.
- **Continuous or high-cardinality `Z`.** Exact matching breaks down. Requires
  either a coarsening whose cost is quantified (see A2) or a conditional
  randomisation approach that models `P(A | Z)`.
- **Choosing the binning.** Currently fixed a priori at 8 pooled quantile bins.
  Selecting it by looking at results would be a garden-of-forking-paths problem;
  selecting it on held-out data would not.
- **Multiplicity.** Auditing several attributes, or several score dimensions,
  needs an explicit correction. None is implemented.
- **Interpretation.** Rejecting `H0` says the score carries information about `A`
  beyond `Z`. It does not identify a mechanism, and under A2 it does not
  distinguish genuine off-criterion dependence from imperfect measurement of the
  construct. That ambiguity is intrinsic, not a limitation of this
  implementation.
