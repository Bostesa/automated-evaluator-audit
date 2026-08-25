"""Tests of score discretisation.

The critical property is structural rather than numerical: the discretisation
must be a function of ``(s, z)`` alone.  The first test enforces that
mechanically by inspecting the function signatures, so a future contributor
cannot quietly introduce an ``a``-dependent binning rule -- which would destroy
the exactness of the permutation null while leaving every simulation looking
superficially fine.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from offcriterion import discretize as discretize_module
from offcriterion.data import RawSample
from offcriterion.discretize import (
    discretize,
    global_quantile_bins,
    quantile_bin_edges,
    within_stratum_quantile_bins,
)


def test_no_binning_function_can_see_the_attribute() -> None:
    """Structural guard: no public binning routine accepts an attribute argument."""
    for name, fn in vars(discretize_module).items():
        if name.startswith("_") or not inspect.isfunction(fn):
            continue
        parameters = set(inspect.signature(fn).parameters)
        assert "a" not in parameters, f"{name} takes an attribute argument"
        assert "attribute" not in parameters, f"{name} takes an attribute argument"


def test_binning_is_unchanged_when_the_attribute_is_permuted() -> None:
    rng = np.random.default_rng(1)
    n = 400
    s = rng.standard_normal(n)
    z = rng.integers(0, 3, n).astype(np.int64)
    a = rng.integers(0, 2, n).astype(np.int64)

    first = discretize(RawSample(s=s, a=a, z=z), n_bins=6)
    second = discretize(RawSample(s=s, a=rng.permutation(a), z=z), n_bins=6)
    assert np.array_equal(first.s_bin, second.s_bin)
    assert first.n_s_bins == second.n_s_bins


def test_global_quantile_bins_are_roughly_balanced() -> None:
    rng = np.random.default_rng(2)
    s = rng.standard_normal(4000)
    codes, k = global_quantile_bins(s, 8)
    assert k == 8
    counts = np.bincount(codes)
    assert counts.min() >= 400 and counts.max() <= 600


def test_quantile_bins_are_monotone_in_the_score() -> None:
    rng = np.random.default_rng(3)
    s = rng.standard_normal(500)
    codes, _ = global_quantile_bins(s, 5)
    order = np.argsort(s)
    assert np.all(np.diff(codes[order]) >= 0)


def test_heavy_ties_collapse_bins_without_error() -> None:
    """A constant score yields a single bin: a resolution loss, not a failure."""
    s = np.zeros(50)
    codes, k = global_quantile_bins(s, 8)
    assert k == 1
    assert np.array_equal(codes, np.zeros(50, dtype=np.int64))


def test_within_stratum_binning_uses_stratum_specific_cuts() -> None:
    """Strata with wildly different score locations each get the full resolution."""
    s = np.concatenate([np.linspace(0.0, 1.0, 100), np.linspace(100.0, 101.0, 100)])
    z = np.repeat([0, 1], 100).astype(np.int64)
    codes, k = within_stratum_quantile_bins(s, z, 4)
    assert k == 4
    for value in (0, 1):
        assert set(np.unique(codes[z == value]).tolist()) == {0, 1, 2, 3}


def test_global_binning_does_not_separate_strata_the_same_way() -> None:
    """Contrast with the previous test: pooled cuts put each stratum in one bin."""
    s = np.concatenate([np.linspace(0.0, 1.0, 100), np.linspace(100.0, 101.0, 100)])
    z = np.repeat([0, 1], 100).astype(np.int64)
    codes, _ = global_quantile_bins(s, 2)
    assert set(np.unique(codes[z == 0]).tolist()) == {0}
    assert set(np.unique(codes[z == 1]).tolist()) == {1}


def test_identity_strategy_relabels_discrete_scores() -> None:
    raw = RawSample(
        s=np.array([1.0, 3.0, 5.0, 3.0]),
        a=np.array([0, 1, 0, 1], dtype=np.int64),
        z=np.zeros(4, dtype=np.int64),
    )
    sample = discretize(raw, strategy="identity")
    assert sample.n_s_bins == 3
    assert np.array_equal(sample.s_bin, np.array([0, 1, 2, 1]))


def test_bin_edges_require_at_least_two_bins() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        quantile_bin_edges(np.arange(10.0), 1)


def test_unknown_strategy_raises() -> None:
    raw = RawSample(
        s=np.arange(4.0), a=np.zeros(4, dtype=np.int64), z=np.zeros(4, dtype=np.int64)
    )
    with pytest.raises(ValueError, match="unknown binning strategy"):
        discretize(raw, strategy="nonsense")  # type: ignore[arg-type]
