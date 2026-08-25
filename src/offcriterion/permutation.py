"""Stratified permutation machinery.

The auditor holds ``S`` and ``Z`` fixed and permutes ``A`` **only within
identical ``Z`` strata**.  Nothing is ever moved across a stratum boundary, so
the attribute counts inside every stratum are preserved exactly.

Why this is the exact conditional null
--------------------------------------
Condition on the whole data except the attribute labels.  Under i.i.d. sampling
from ``P(S, A, Z)`` and under ``H0 : S _||_ A | Z``,

    P(A_1..A_n | S_1..S_n, Z_1..Z_n)
        = prod_i P(A_i | S_i, Z_i)          [i.i.d. sampling]
        = prod_i P(A_i | Z_i)               [this equality *is* H0]

Inside a stratum ``{i : Z_i = z}`` every factor is the same law ``P(A | Z = z)``,
so the labels there are exchangeable, independently across strata.  Conditioning
further on the observed multiset of labels in each stratum, every within-stratum
arrangement is equally likely.  The within-stratum permutation distribution is
therefore the *exact* conditional null distribution of any statistic -- no
asymptotics, and no assumption whatsoever about the shape of ``P(S | Z)``.

What this argument does and does not buy is spelled out in
``docs/assumptions.md``.  In particular the exactness claim is a *mathematical*
statement conditional on its hypotheses; the simulations in this repository are
evidence that the implementation matches the mathematics, and are not themselves
a proof of finite-sample validity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np

from offcriterion.data import FloatArray, IntArray, Sample, Strata
from offcriterion.statistics import DEFAULT_STATISTICS, get_statistic


def permute_within_strata(
    a: IntArray, strata: Strata, rng: np.random.Generator
) -> IntArray:
    """Return a copy of ``a`` independently permuted inside each ``Z`` stratum.

    Guarantees, all directly unit-tested:

    * no element is relocated across strata;
    * the multiset of attribute values inside each stratum is preserved exactly;
    * the draw is uniform over the product of the within-stratum symmetric
      groups, independently across strata.
    """
    permuted = a.copy()
    for group in strata.groups:
        if group.size > 1:
            permuted[group] = a[rng.permutation(group)]
    return permuted


@dataclass(frozen=True)
class PermutationTestResult:
    """Outcome of one stratified permutation test."""

    statistic: str
    observed: float
    p_value: float
    n_permutations: int
    n_at_least_observed: int
    n: int
    n_strata: int
    n_usable_strata: int

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


def _monte_carlo_p_value(
    observed: float, null_values: FloatArray, tie_rtol: float
) -> tuple[float, int]:
    """``p = (1 + #{T_b >= T_obs}) / (B + 1)``.

    Never returns zero: the observed statistic is counted as one of the ``B + 1``
    draws from the null, which is what makes this a valid Monte Carlo test rather
    than an estimate of an unattainable exact p-value.

    Near-ties are resolved *towards* counting, using a relative tolerance.  With
    a discrete statistic on sparse tables exact ties are common, and floating
    point noise must not be allowed to break them in the anti-conservative
    direction.  This can only inflate the p-value, so the test stays valid and
    becomes slightly conservative.
    """
    tol = tie_rtol * max(1.0, abs(observed))
    n_ge = int(np.count_nonzero(null_values >= observed - tol))
    p = (1.0 + n_ge) / (null_values.size + 1.0)
    return p, n_ge


def permutation_null_distribution(
    sample: Sample,
    statistic_names: Sequence[str],
    n_permutations: int,
    rng: np.random.Generator,
) -> tuple[dict[str, float], dict[str, FloatArray], Strata]:
    """Observed statistics and their shared permutation null distributions.

    All statistics are evaluated on the *same* permutation draws.  That makes the
    columns of the results table paired, so differences between them reflect the
    statistics and not independent Monte Carlo noise.
    """
    if n_permutations < 1:
        raise ValueError(f"n_permutations must be at least 1, got {n_permutations}")

    strata = Strata.from_codes(sample.z)
    prepared = {name: get_statistic(name).prepare(sample) for name in statistic_names}
    observed = {name: float(fn(sample.a)) for name, fn in prepared.items()}
    null = {name: np.empty(n_permutations, dtype=np.float64) for name in statistic_names}

    for b in range(n_permutations):
        a_perm = permute_within_strata(sample.a, strata, rng)
        for name, fn in prepared.items():
            null[name][b] = fn(a_perm)

    return observed, null, strata


def permutation_test(
    sample: Sample,
    statistic_names: Iterable[str] = DEFAULT_STATISTICS,
    n_permutations: int = 999,
    rng: np.random.Generator | None = None,
    *,
    tie_rtol: float = 1e-9,
) -> dict[str, PermutationTestResult]:
    """Run the stratified permutation test for one or more statistics.

    Parameters
    ----------
    sample:
        Discretised sample.  Its ``s_bin`` must already have been computed from
        ``(s_raw, z)`` alone -- see :mod:`offcriterion.discretize`.
    statistic_names:
        Names registered in :data:`offcriterion.statistics.STATISTICS`.
    n_permutations:
        ``B``.  P-values live on the grid ``{1/(B+1), ..., 1}``, so ``B`` should
        be large enough that ``alpha`` is representable; ``B = 999`` suffices for
        ``alpha = 0.05``.
    rng:
        Seeded generator.  Required for reproducibility; a fresh default
        generator is used if omitted.
    """
    names = tuple(statistic_names)
    generator = np.random.default_rng() if rng is None else rng
    observed, null, strata = permutation_null_distribution(
        sample, names, n_permutations, generator
    )
    n_usable = strata.n_usable(sample.a)

    results: dict[str, PermutationTestResult] = {}
    for name in names:
        p, n_ge = _monte_carlo_p_value(observed[name], null[name], tie_rtol)
        results[name] = PermutationTestResult(
            statistic=name,
            observed=observed[name],
            p_value=p,
            n_permutations=n_permutations,
            n_at_least_observed=n_ge,
            n=sample.n,
            n_strata=strata.n_strata,
            n_usable_strata=n_usable,
        )
    return results


def p_values(results: Mapping[str, PermutationTestResult]) -> dict[str, float]:
    return {name: res.p_value for name, res in results.items()}
