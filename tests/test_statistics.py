"""Tests of the test statistics.

Two kinds of check:

* **hand-constructed examples** with closed-form answers, so the statistics are
  pinned to their definitions rather than to whatever the code happens to do;
* **oracle agreement**, comparing the fast ``prepare`` path (which caches
  quantities that within-stratum permutation leaves invariant) against a naive
  ``reference`` implementation that recomputes everything from scratch.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from offcriterion.data import RawSample, Sample, Strata
from offcriterion.discretize import discretize
from offcriterion.permutation import permute_within_strata
from offcriterion.statistics import STATISTICS, get_statistic

G2 = STATISTICS["conditional_g2"]
CMI = STATISTICS["conditional_mi"]
MEAN = STATISTICS["stratified_mean_disparity"]
LRT = STATISTICS["stratified_regression_lrt"]


def sample_from(s: list[float], a: list[int], z: list[int], *, strategy: str = "identity") -> Sample:
    raw = RawSample(
        s=np.asarray(s, dtype=np.float64),
        a=np.asarray(a, dtype=np.int64),
        z=np.asarray(z, dtype=np.int64),
    )
    return discretize(raw, strategy=strategy)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Hand-constructed examples
# --------------------------------------------------------------------------


def test_g2_is_zero_under_exact_conditional_independence() -> None:
    """A 2x2 table equal to the product of its margins carries no information."""
    sample = sample_from([0, 0, 1, 1], [0, 1, 0, 1], [0, 0, 0, 0])
    assert G2(sample) == pytest.approx(0.0, abs=1e-12)
    assert CMI(sample) == pytest.approx(0.0, abs=1e-12)


def test_g2_on_perfect_dependence_matches_closed_form() -> None:
    """s determines a exactly: I(S; A | Z) = log 2 nats, so G^2 = 2 n log 2."""
    sample = sample_from([0, 0, 1, 1], [0, 0, 1, 1], [0, 0, 0, 0])
    assert G2(sample) == pytest.approx(8.0 * math.log(2.0))
    assert CMI(sample) == pytest.approx(math.log(2.0))


def test_g2_ignores_dependence_that_is_explained_by_the_stratum() -> None:
    """Within every stratum, s is constant, so nothing is left for a to explain."""
    sample = sample_from([0, 0, 1, 1], [0, 1, 0, 1], [0, 0, 1, 1])
    assert G2(sample) == pytest.approx(0.0, abs=1e-12)


def test_conditional_mi_is_g2_over_two_n() -> None:
    rng = np.random.default_rng(0)
    n = 200
    raw = RawSample(
        s=rng.standard_normal(n),
        a=rng.integers(0, 3, n).astype(np.int64),
        z=rng.integers(0, 4, n).astype(np.int64),
    )
    sample = discretize(raw, n_bins=5)
    assert CMI(sample) == pytest.approx(G2(sample) / (2 * n))


def test_mean_disparity_matches_closed_form() -> None:
    """Stratum 0 contributes |0 - 2| at weight 1/2; stratum 1 contributes 0."""
    sample = sample_from([0, 2, 5, 5], [0, 1, 0, 1], [0, 0, 1, 1])
    assert MEAN(sample) == pytest.approx(1.0)


def test_mean_disparity_is_zero_when_conditional_means_match() -> None:
    sample = sample_from([-2, 2, -1, 1], [0, 0, 1, 1], [0, 0, 0, 0])
    assert MEAN(sample) == pytest.approx(0.0, abs=1e-12)


def test_regression_lrt_matches_closed_form() -> None:
    """RSS0 = 5, RSS1 = 1, n = 4  =>  T = 4 log 5."""
    sample = sample_from([0, 1, 2, 3], [0, 0, 1, 1], [0, 0, 0, 0])
    assert LRT(sample) == pytest.approx(4.0 * math.log(5.0))


def test_regression_lrt_is_zero_when_cell_means_match_stratum_means() -> None:
    sample = sample_from([-2, 2, -1, 1], [0, 0, 1, 1], [0, 0, 0, 0])
    assert LRT(sample) == pytest.approx(0.0, abs=1e-12)


def test_table_statistic_sees_a_scale_difference_the_mean_statistics_score_at_zero() -> None:
    """The motivating case, in miniature.

    Group ``a = 0`` is dispersed, group ``a = 1`` is concentrated, and both have
    conditional mean zero.  Both mean-oriented statistics return exactly zero;
    the contingency-table statistic does not.
    """
    s = [-3.0, -1.0, 1.0, 3.0, -0.2, -0.1, 0.1, 0.2]
    a = [0, 0, 0, 0, 1, 1, 1, 1]
    z = [0] * 8
    sample = discretize(
        RawSample(s=np.asarray(s), a=np.asarray(a, dtype=np.int64), z=np.asarray(z, dtype=np.int64)),
        n_bins=4,
        strategy="global_quantile",
    )
    assert MEAN(sample) == pytest.approx(0.0, abs=1e-12)
    assert LRT(sample) == pytest.approx(0.0, abs=1e-9)
    assert G2(sample) > 1.0


# --------------------------------------------------------------------------
# Structural properties
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(STATISTICS))
@pytest.mark.parametrize("seed", range(5))
def test_statistics_are_non_negative(name: str, seed: int) -> None:
    """All four are oriented so that larger means more evidence against H0."""
    rng = np.random.default_rng(seed)
    n = 150
    z = rng.integers(0, 3, n).astype(np.int64)
    raw = RawSample(s=rng.standard_normal(n) + z, a=rng.integers(0, 2, n).astype(np.int64), z=z)
    sample = discretize(raw, n_bins=5)
    assert get_statistic(name)(sample) >= -1e-12


@pytest.mark.parametrize("name", sorted(STATISTICS))
def test_prepared_path_agrees_with_naive_reference(name: str) -> None:
    """The cached fast path must equal the from-scratch recomputation.

    Checked over many *valid* within-stratum permutations, which is the only
    input class the fast path claims to handle: it caches the stratum-by-
    attribute counts, and those are invariant under exactly this class of
    relabellings (see ``tests/test_permutation.py``).
    """
    rng = np.random.default_rng(17)
    n = 180
    z = rng.integers(0, 4, n).astype(np.int64)
    raw = RawSample(s=rng.standard_normal(n) + z, a=rng.integers(0, 3, n).astype(np.int64), z=z)
    sample = discretize(raw, n_bins=5)

    statistic = get_statistic(name)
    evaluate = statistic.prepare(sample)
    strata = Strata.from_codes(sample.z)

    assert evaluate(sample.a) == pytest.approx(statistic.reference(sample))
    for _ in range(50):
        a_perm = permute_within_strata(sample.a, strata, rng)
        assert evaluate(a_perm) == pytest.approx(statistic.reference(sample, a_perm))


def test_statistics_handle_empty_and_singleton_cells() -> None:
    """Sparse strata must not raise, produce NaN, or produce infinities."""
    s = [0.0, 1.0, 2.0, 3.0, 4.0]
    a = [0, 0, 1, 0, 1]
    z = [0, 0, 0, 1, 2]  # z=1 has only a=0; z=2 is a singleton
    sample = sample_from(s, a, z)
    for name in STATISTICS:
        value = get_statistic(name)(sample)
        assert np.isfinite(value), f"{name} produced {value}"


def test_unknown_statistic_name_raises() -> None:
    with pytest.raises(KeyError, match="unknown statistic"):
        get_statistic("not_a_statistic")
