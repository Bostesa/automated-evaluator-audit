"""Empirical calibration checks under known nulls.

Read the scope of these tests carefully.

They are **implementation checks**, not proofs.  The exactness of the stratified
permutation test is a mathematical result that follows from the assumptions set
out in ``docs/assumptions.md``; simulation cannot establish it, and a passing run
here must never be reported as "finite-sample validity was verified".  What these
tests can do -- and what they are for -- is detect an implementation that
contradicts the mathematics: a leak across strata, an attribute-dependent
preprocessing step, a mis-stated p-value formula.  Any of those would show up as
a rejection rate that drifts away from nominal.

They are also intrinsically noisy.  Every bound below is stated as an explicit
multiple of the binomial Monte Carlo standard error at the configured replicate
count, so a failure means "further from nominal than sampling noise explains",
not "not exactly 0.05".
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from offcriterion.discretize import discretize
from offcriterion.permutation import permutation_test
from offcriterion.scenarios import get_scenario

pytestmark = pytest.mark.slow

REPLICATES = 600
PERMUTATIONS = 199
N = 250
ALPHA = 0.05
SEED = 20240817

STATISTICS = ("conditional_g2", "stratified_mean_disparity", "stratified_regression_lrt")


def monte_carlo_se(p: float, replicates: int = REPLICATES) -> float:
    return math.sqrt(p * (1.0 - p) / replicates)


def null_p_values(
    scenario_name: str,
    *,
    n: int = N,
    replicates: int = REPLICATES,
    permutations: int = PERMUTATIONS,
    seed: int = SEED,
) -> dict[str, np.ndarray]:
    """Run repeated independent experiments and collect p-values per statistic."""
    scenario = get_scenario(scenario_name)
    collected: dict[str, list[float]] = {name: [] for name in STATISTICS}
    for replicate in range(replicates):
        data_rng = np.random.default_rng(
            np.random.SeedSequence(entropy=seed, spawn_key=(replicate, 0))
        )
        perm_rng = np.random.default_rng(
            np.random.SeedSequence(entropy=seed, spawn_key=(replicate, 1))
        )
        sample = discretize(scenario(n, data_rng), n_bins=8)
        results = permutation_test(sample, STATISTICS, permutations, perm_rng)
        for name in STATISTICS:
            collected[name].append(results[name].p_value)
    return {name: np.asarray(values) for name, values in collected.items()}


# --------------------------------------------------------------------------
# Requirement: under a simple known null, repeated experiments approximately
# recover the nominal Type I error rate.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_name", ["conditional_null", "confounded_observed"])
def test_type_one_error_is_close_to_nominal(scenario_name: str) -> None:
    """Both scenarios satisfy ``S _||_ A | Z`` exactly by construction."""
    p_values = null_p_values(scenario_name)
    tolerance = 4.0 * monte_carlo_se(ALPHA)
    for name, values in p_values.items():
        rate = float(np.mean(values <= ALPHA))
        assert rate <= ALPHA + tolerance, (
            f"{scenario_name}/{name}: rejection rate {rate:.4f} exceeds "
            f"{ALPHA} + 4 MC SE = {ALPHA + tolerance:.4f}"
        )


def test_continuous_statistic_is_not_merely_conservative() -> None:
    """A near-continuous statistic should sit *at* nominal, not far below it.

    Included because "rejects less than alpha" is satisfied by a test that never
    rejects.  The mean-disparity statistic has an almost continuous permutation
    distribution, so its rejection rate should track alpha closely; the discrete
    table statistic is allowed to be conservative through ties.
    """
    values = null_p_values("conditional_null")["stratified_mean_disparity"]
    rate = float(np.mean(values <= ALPHA))
    tolerance = 4.0 * monte_carlo_se(ALPHA)
    assert ALPHA - tolerance <= rate <= ALPHA + tolerance, f"rejection rate {rate:.4f}"


@pytest.mark.parametrize("alpha", [0.01, 0.05, 0.10, 0.20])
def test_null_p_values_are_super_uniform(alpha: float) -> None:
    """``P(p <= alpha) <= alpha`` at several levels, not just at 0.05.

    A test calibrated only at one level would pass the headline check while being
    wrong everywhere else, so the whole lower tail of the p-value distribution is
    checked.
    """
    p_values = null_p_values("conditional_null")
    for name, values in p_values.items():
        rate = float(np.mean(values <= alpha))
        tolerance = 4.0 * monte_carlo_se(alpha)
        assert rate <= alpha + tolerance, f"{name} at alpha={alpha}: {rate:.4f}"


def test_conservativeness_of_the_table_statistic_comes_from_ties() -> None:
    """Document the mechanism rather than just tolerating the symptom."""
    scenario = get_scenario("conditional_null")
    sample = discretize(scenario(N, np.random.default_rng(0)), n_bins=8)
    from offcriterion.permutation import permutation_null_distribution

    observed, null, _ = permutation_null_distribution(
        sample, STATISTICS, 2000, np.random.default_rng(1)
    )
    distinct = {name: np.unique(values).size for name, values in null.items()}
    # The G^2 permutation distribution is far more tied than the mean statistic's.
    assert distinct["conditional_g2"] < distinct["stratified_mean_disparity"]


# --------------------------------------------------------------------------
# Power behaves as designed
# --------------------------------------------------------------------------


def test_power_increases_with_sample_size_under_mean_dependence() -> None:
    small = null_p_values("mean_dependence", n=150, replicates=200)
    large = null_p_values("mean_dependence", n=900, replicates=200)
    for name in STATISTICS:
        assert float(np.mean(large[name] <= ALPHA)) > float(np.mean(small[name] <= ALPHA)), name


def test_only_the_table_statistic_detects_variance_only_dependence() -> None:
    p_values = null_p_values("variance_only", n=600, replicates=200)
    tolerance = 4.0 * monte_carlo_se(ALPHA, 200)
    assert float(np.mean(p_values["conditional_g2"] <= ALPHA)) > 0.5
    for name in ("stratified_mean_disparity", "stratified_regression_lrt"):
        rate = float(np.mean(p_values[name] <= ALPHA))
        assert rate <= ALPHA + tolerance, f"{name} should be powerless here, got {rate:.4f}"


def test_only_the_table_statistic_detects_shape_only_dependence() -> None:
    p_values = null_p_values("shape_only", n=1200, replicates=200)
    tolerance = 4.0 * monte_carlo_se(ALPHA, 200)
    assert float(np.mean(p_values["conditional_g2"] <= ALPHA)) > 0.25
    for name in ("stratified_mean_disparity", "stratified_regression_lrt"):
        rate = float(np.mean(p_values[name] <= ALPHA))
        assert rate <= ALPHA + tolerance, f"{name} should be powerless here, got {rate:.4f}"


def test_noisy_proxy_produces_residual_dependence() -> None:
    """Not a Type I error: conditioning on a coarsened proxy makes the null false."""
    p_values = null_p_values("confounded_proxy", n=600, replicates=200)
    assert float(np.mean(p_values["conditional_g2"] <= ALPHA)) > 0.2
