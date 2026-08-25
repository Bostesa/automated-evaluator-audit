"""Tests of the data containers and stratum index."""

from __future__ import annotations

import numpy as np
import pytest

from offcriterion.data import RawSample, Strata


def test_strata_partition_every_row_exactly_once() -> None:
    rng = np.random.default_rng(0)
    z = rng.integers(0, 6, 500).astype(np.int64)
    strata = Strata.from_codes(z)
    covered = np.concatenate(strata.groups)
    assert np.array_equal(np.sort(covered), np.arange(500))
    assert strata.sizes().sum() == 500


def test_strata_groups_are_homogeneous_in_z() -> None:
    rng = np.random.default_rng(1)
    z = rng.integers(0, 5, 300).astype(np.int64)
    strata = Strata.from_codes(z)
    for group, value in zip(strata.groups, strata.unique_z):
        assert np.all(z[group] == value)


def test_strata_recover_all_distinct_levels() -> None:
    z = np.array([3, 0, 3, 7, 0], dtype=np.int64)
    strata = Strata.from_codes(z)
    assert strata.n_strata == 3
    assert np.array_equal(strata.unique_z, np.array([0, 3, 7]))


def test_raw_sample_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        RawSample(
            s=np.zeros(5), a=np.zeros(4, dtype=np.int64), z=np.zeros(5, dtype=np.int64)
        )


def test_raw_sample_rejects_non_integer_codes() -> None:
    with pytest.raises(TypeError, match="category codes"):
        RawSample(s=np.zeros(3), a=np.zeros(3), z=np.zeros(3, dtype=np.int64))


def test_raw_sample_rejects_non_finite_scores() -> None:
    with pytest.raises(ValueError, match="finite"):
        RawSample(
            s=np.array([0.0, np.nan]),
            a=np.zeros(2, dtype=np.int64),
            z=np.zeros(2, dtype=np.int64),
        )


def test_raw_sample_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        RawSample(
            s=np.zeros(0), a=np.zeros(0, dtype=np.int64), z=np.zeros(0, dtype=np.int64)
        )
