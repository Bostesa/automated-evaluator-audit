"""Tests of the permutation scheme itself.

These are the tests that protect the validity claim.  If any of them fails, the
reference distribution is not the conditional null distribution and every
p-value in the repository is meaningless.
"""

from __future__ import annotations

import itertools
from collections import Counter

import numpy as np
import pytest

from offcriterion.data import RawSample, Sample, Strata
from offcriterion.discretize import discretize
from offcriterion.permutation import (
    _monte_carlo_p_value,
    permutation_null_distribution,
    permutation_test,
    permute_within_strata,
)
from offcriterion.scenarios import SCENARIOS
from offcriterion.statistics import STATISTICS


def make_sample(n: int = 240, seed: int = 7) -> Sample:
    rng = np.random.default_rng(seed)
    z = rng.integers(0, 4, size=n).astype(np.int64)
    a = rng.integers(0, 2, size=n).astype(np.int64)
    s = rng.standard_normal(n) + z
    return discretize(RawSample(s=s, a=a, z=z), n_bins=5)


# --------------------------------------------------------------------------
# Requirement: permutation never crosses conditioning strata
# --------------------------------------------------------------------------


def test_permutation_never_crosses_strata() -> None:
    sample = make_sample()
    strata = Strata.from_codes(sample.z)
    rng = np.random.default_rng(0)

    for _ in range(200):
        permuted = permute_within_strata(sample.a, strata, rng)
        for group in strata.groups:
            # The multiset of labels inside the stratum is untouched.
            assert Counter(sample.a[group].tolist()) == Counter(permuted[group].tolist())


def test_permutation_moves_only_within_stratum_positions() -> None:
    """Any position whose label changed must have taken it from its own stratum."""
    n = 60
    rng = np.random.default_rng(3)
    z = np.repeat(np.arange(3), n // 3).astype(np.int64)
    # A label unique to each stratum makes cross-stratum leakage detectable.
    a = z.copy()
    strata = Strata.from_codes(z)
    for _ in range(100):
        permuted = permute_within_strata(a, strata, rng)
        assert np.array_equal(permuted, a), "labels constant within stratum must be immovable"


def test_cross_stratum_permutation_is_detectably_different() -> None:
    """Negative control: a *global* shuffle does break the stratum counts."""
    n = 60
    z = np.repeat(np.arange(3), n // 3).astype(np.int64)
    a = z.copy()
    rng = np.random.default_rng(5)
    global_shuffle = rng.permutation(a)
    assert not np.array_equal(global_shuffle, a)


# --------------------------------------------------------------------------
# Requirement: stratum attribute counts are preserved exactly
# --------------------------------------------------------------------------


def test_stratum_attribute_counts_preserved_exactly() -> None:
    sample = make_sample()
    strata = Strata.from_codes(sample.z)
    rng = np.random.default_rng(11)

    def table(a: np.ndarray) -> np.ndarray:
        return np.bincount(sample.z * sample.n_a + a, minlength=sample.n_z * sample.n_a)

    observed = table(sample.a)
    for _ in range(300):
        assert np.array_equal(table(permute_within_strata(sample.a, strata, rng)), observed)


def test_score_binning_is_invariant_under_permutation() -> None:
    """The permutation rewrites ``a`` only; ``s_raw``, ``s_bin`` and ``z`` are fixed."""
    sample = make_sample()
    strata = Strata.from_codes(sample.z)
    rng = np.random.default_rng(13)
    before = (sample.s_raw.copy(), sample.s_bin.copy(), sample.z.copy())
    permute_within_strata(sample.a, strata, rng)
    assert np.array_equal(sample.s_raw, before[0])
    assert np.array_equal(sample.s_bin, before[1])
    assert np.array_equal(sample.z, before[2])


# --------------------------------------------------------------------------
# Requirement: the draw is uniform over the within-stratum symmetric group
# --------------------------------------------------------------------------


def test_permutation_draw_is_uniform_within_stratum() -> None:
    """All 3! arrangements of three distinct labels appear about equally often."""
    z = np.zeros(3, dtype=np.int64)
    a = np.array([0, 1, 2], dtype=np.int64)
    strata = Strata.from_codes(z)
    rng = np.random.default_rng(2024)

    draws = Counter(tuple(permute_within_strata(a, strata, rng).tolist()) for _ in range(6000))
    assert set(draws) == set(itertools.permutations([0, 1, 2]))
    counts = np.array(list(draws.values()), dtype=float)
    chi_square = float(((counts - 1000.0) ** 2 / 1000.0).sum())
    assert chi_square < 20.5, f"chi-square {chi_square} exceeds the 0.999 quantile on 5 df"


# --------------------------------------------------------------------------
# Requirement: the Monte Carlo p-value is always in (0, 1]
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n_permutations", [1, 9, 99])
@pytest.mark.parametrize("seed", range(6))
def test_p_value_in_open_unit_interval(n_permutations: int, seed: int) -> None:
    sample = make_sample(n=120, seed=seed)
    results = permutation_test(
        sample, tuple(STATISTICS), n_permutations, np.random.default_rng(seed)
    )
    for result in results.values():
        assert 0.0 < result.p_value <= 1.0
        # Attainable minimum is exactly 1/(B+1); zero is unreachable by construction.
        assert result.p_value >= 1.0 / (n_permutations + 1)
        assert result.p_value == pytest.approx(
            (1 + result.n_at_least_observed) / (n_permutations + 1)
        )


def test_p_value_formula_extremes() -> None:
    # Observed larger than every permuted value -> smallest attainable p-value.
    p, n_ge = _monte_carlo_p_value(10.0, np.zeros(99), tie_rtol=1e-9)
    assert (p, n_ge) == (1 / 100, 0)
    # Observed smaller than every permuted value -> p = 1.
    p, n_ge = _monte_carlo_p_value(-10.0, np.zeros(99), tie_rtol=1e-9)
    assert (p, n_ge) == (1.0, 99)


def test_near_ties_are_resolved_conservatively() -> None:
    """Floating point noise must never push a tie in the anti-conservative direction."""
    observed = 3.0
    null = np.full(999, observed) * (1 - 1e-12)  # imperceptibly below
    p, n_ge = _monte_carlo_p_value(observed, null, tie_rtol=1e-9)
    assert n_ge == 999
    assert p == 1.0


# --------------------------------------------------------------------------
# Exactness of the machinery: exhaustive enumeration on a tiny problem
# --------------------------------------------------------------------------


def test_monte_carlo_p_value_converges_to_exhaustive_permutation_p_value() -> None:
    """Compare the Monte Carlo p-value against the full permutation distribution.

    This checks the *machinery*, not the calibration: for a problem small enough
    to enumerate, the exact conditional p-value is computable, and the Monte
    Carlo estimate must land on it as B grows.
    """
    s = np.array([0.0, 1.0, 2.0, 3.0, 0.5, 2.5], dtype=np.float64)
    a = np.array([0, 0, 1, 1, 0, 1], dtype=np.int64)
    z = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
    sample = discretize(RawSample(s=s, a=a, z=z), strategy="global_quantile", n_bins=3)

    statistic = STATISTICS["conditional_g2"]
    evaluate = statistic.prepare(sample)
    observed = evaluate(sample.a)

    # Enumerate the product of the two within-stratum symmetric groups.
    groups = [np.flatnonzero(z == value) for value in np.unique(z)]
    exact_values = []
    for arrangement in itertools.product(*(itertools.permutations(a[g]) for g in groups)):
        candidate = a.copy()
        for group, labels in zip(groups, arrangement):
            candidate[group] = np.asarray(labels, dtype=np.int64)
        exact_values.append(evaluate(candidate))
    exact_values_arr = np.asarray(exact_values)
    exact_p = float(np.mean(exact_values_arr >= observed - 1e-9))

    result = permutation_test(sample, ("conditional_g2",), 20000, np.random.default_rng(42))[
        "conditional_g2"
    ]
    assert result.p_value == pytest.approx(exact_p, abs=0.02)


# --------------------------------------------------------------------------
# Requirement: identical seeds reproduce identical results
# --------------------------------------------------------------------------


def test_identical_seeds_reproduce_identical_results() -> None:
    sample = make_sample()
    first = permutation_test(sample, tuple(STATISTICS), 199, np.random.default_rng(99))
    second = permutation_test(sample, tuple(STATISTICS), 199, np.random.default_rng(99))
    assert {k: v.to_dict() for k, v in first.items()} == {k: v.to_dict() for k, v in second.items()}


def test_different_seeds_give_different_null_draws() -> None:
    sample = make_sample()
    _, null_a, _ = permutation_null_distribution(sample, ("conditional_g2",), 199, np.random.default_rng(1))
    _, null_b, _ = permutation_null_distribution(sample, ("conditional_g2",), 199, np.random.default_rng(2))
    assert not np.array_equal(null_a["conditional_g2"], null_b["conditional_g2"])


def test_statistics_share_one_set_of_permutations() -> None:
    """Paired columns: the observed statistic must not depend on which set was asked for."""
    sample = make_sample()
    together = permutation_test(sample, ("conditional_g2", "stratified_mean_disparity"), 99, np.random.default_rng(4))
    alone = permutation_test(sample, ("conditional_g2",), 99, np.random.default_rng(4))
    assert together["conditional_g2"].observed == pytest.approx(alone["conditional_g2"].observed)
    assert together["conditional_g2"].p_value == pytest.approx(alone["conditional_g2"].p_value)


def test_rejects_non_positive_permutation_count() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        permutation_test(make_sample(), ("conditional_g2",), 0, np.random.default_rng(0))


def test_usable_strata_excludes_singletons_and_constant_attribute() -> None:
    z = np.array([0, 0, 1, 2, 2], dtype=np.int64)
    a = np.array([0, 1, 0, 1, 1], dtype=np.int64)  # z=1 singleton; z=2 constant a
    strata = Strata.from_codes(z)
    assert strata.n_strata == 3
    assert strata.n_usable(a) == 1
