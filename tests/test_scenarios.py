"""Tests that the synthetic scenarios generate what they claim to generate.

A scenario that silently fails to match its own description would make the whole
results table meaningless -- a "variance-only" alternative that also shifted the
mean would let the mean baselines pass a test they should fail.  These checks
pin each scenario's moment structure and its ground-truth null status.
"""

from __future__ import annotations

import numpy as np
import pytest

from offcriterion.diagnostics import conditional_moments, population_conditional_mi
from offcriterion.scenarios import (
    NULL_TRUE,
    SCENARIO_ORDER,
    SCENARIOS,
    generate_confounded_observed,
    get_scenario,
    make_confounded_proxy,
)

REFERENCE_N = 200_000
SEED = 1234


def moments(name: str) -> dict[tuple[int, int], dict[str, float]]:
    rows = conditional_moments(get_scenario(name), reference_n=REFERENCE_N, seed=SEED)
    return {(int(r["z"]), int(r["a"])): r for r in rows}


def test_all_six_scenarios_are_registered() -> None:
    assert len(SCENARIO_ORDER) == 6
    assert SCENARIO_ORDER == (
        "conditional_null",
        "mean_dependence",
        "variance_only",
        "shape_only",
        "confounded_observed",
        "confounded_proxy",
    )


def test_scenarios_are_reproducible_from_a_seed() -> None:
    for name, scenario in SCENARIOS.items():
        first = scenario(500, np.random.default_rng(9))
        second = scenario(500, np.random.default_rng(9))
        assert np.array_equal(first.s, second.s), name
        assert np.array_equal(first.a, second.a), name
        assert np.array_equal(first.z, second.z), name


def test_conditioning_is_not_vacuous_in_the_null_scenario() -> None:
    """``A`` must depend on ``Q``; otherwise conditioning tests nothing."""
    raw = SCENARIOS["conditional_null"](200_000, np.random.default_rng(SEED))
    rates = [float(raw.a[raw.z == q].mean()) for q in range(raw.n_z)]
    assert max(rates) - min(rates) > 0.3
    assert np.all(np.diff(rates) > 0), "P(A = 1 | Q) should be monotone in Q"


def test_conditional_null_matches_all_moments_across_the_attribute() -> None:
    cells = moments("conditional_null")
    for z in range(5):
        m0, m1 = cells[(z, 0)], cells[(z, 1)]
        assert m0["mean"] == pytest.approx(m1["mean"], abs=0.05)
        assert m0["variance"] == pytest.approx(m1["variance"], abs=0.05)
        assert m0["excess_kurtosis"] == pytest.approx(m1["excess_kurtosis"], abs=0.15)


def test_mean_dependence_shifts_only_the_mean() -> None:
    cells = moments("mean_dependence")
    for z in range(5):
        m0, m1 = cells[(z, 0)], cells[(z, 1)]
        assert m1["mean"] - m0["mean"] == pytest.approx(0.30, abs=0.05)
        assert m0["variance"] == pytest.approx(m1["variance"], abs=0.05)


def test_variance_only_matches_means_and_separates_variances() -> None:
    cells = moments("variance_only")
    for z in range(5):
        m0, m1 = cells[(z, 0)], cells[(z, 1)]
        assert m0["mean"] == pytest.approx(m1["mean"], abs=0.05), "means must match"
        assert m0["variance"] == pytest.approx(1.0, abs=0.06)
        assert m1["variance"] == pytest.approx(1.6**2, abs=0.15)


def test_shape_only_matches_mean_variance_and_skewness_but_not_kurtosis() -> None:
    """The claim that only the shape differs is verified, not asserted."""
    cells = moments("shape_only")
    for z in range(5):
        m0, m1 = cells[(z, 0)], cells[(z, 1)]
        assert m0["mean"] == pytest.approx(m1["mean"], abs=0.05), "means must match"
        assert m0["variance"] == pytest.approx(m1["variance"], abs=0.06), "variances must match"
        assert m0["skewness"] == pytest.approx(m1["skewness"], abs=0.10), "skewness must match"
        # Only the fourth moment separates the groups.
        assert m1["excess_kurtosis"] - m0["excess_kurtosis"] > 1.0


def test_confounded_observed_satisfies_the_conditional_null() -> None:
    """``S`` depends on ``A`` only through ``Q``, so conditioning on ``Q`` restores independence."""
    cells = moments("confounded_observed")
    for (z, _a), row in cells.items():
        if (z, 0) in cells and (z, 1) in cells and cells[(z, 0)]["n"] > 1000:
            assert cells[(z, 0)]["mean"] == pytest.approx(cells[(z, 1)]["mean"], abs=0.06)
            assert cells[(z, 0)]["variance"] == pytest.approx(cells[(z, 1)]["variance"], abs=0.08)


def test_confounded_scenarios_are_strongly_dependent_marginally() -> None:
    """The whole point: aggregate disparity is large even when the null holds."""
    raw = SCENARIOS["confounded_observed"](200_000, np.random.default_rng(SEED))
    gap = float(raw.s[raw.a == 1].mean() - raw.s[raw.a == 0].mean())
    assert gap > 0.5


def test_noiseless_proxy_recovers_the_observed_construct_scenario() -> None:
    """``tau = 0`` must reproduce scenario 5 exactly, seed for seed."""
    noiseless = make_confounded_proxy(tau=0.0)
    proxy = noiseless(2000, np.random.default_rng(3))
    exact = generate_confounded_observed(2000, np.random.default_rng(3))
    assert np.array_equal(proxy.a, exact.a)
    assert np.array_equal(proxy.s, exact.s)
    assert np.array_equal(proxy.z, exact.z)


def test_noisy_proxy_scrambles_the_conditioning_variable() -> None:
    """With noise, the stratum label no longer pins down ``Q``."""
    proxy = make_confounded_proxy(tau=1.0)(200_000, np.random.default_rng(SEED))
    exact = generate_confounded_observed(200_000, np.random.default_rng(SEED))
    assert not np.array_equal(proxy.z, exact.z)
    agreement = float(np.mean(proxy.z == exact.z))
    assert 0.2 < agreement < 0.8, f"proxy agreement {agreement} is degenerate"


# --------------------------------------------------------------------------
# Design diagnostics: is each alternative actually visible at the binning we use?
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["mean_dependence", "variance_only", "shape_only"])
def test_alternatives_carry_signal_at_the_default_binning(name: str) -> None:
    """Guards against reporting a design artifact as a finding.

    If the population conditional mutual information induced by the binning were
    near zero, low power would say nothing about the statistic.
    """
    diagnostic = population_conditional_mi(get_scenario(name), n_bins=8, reference_n=200_000)
    assert diagnostic.detectable, f"{name} is not detectable at 8 bins: {diagnostic}"
    assert diagnostic.conditional_mi > 1e-3


@pytest.mark.parametrize("name", ["conditional_null", "confounded_observed"])
def test_null_scenarios_carry_no_population_signal(name: str) -> None:
    """Under a true null the population CMI is zero; the estimate sits at the bias floor."""
    diagnostic = population_conditional_mi(get_scenario(name), n_bins=8, reference_n=200_000)
    assert get_scenario(name).null_status == NULL_TRUE
    assert diagnostic.conditional_mi < 10.0 * diagnostic.plug_in_bias_bound
