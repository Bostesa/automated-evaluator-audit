"""Test statistics for the stratified conditional-independence audit.

Design contract
---------------
A statistic is an object with

* ``name``            -- identifier used in result files;
* ``sensitivity``     -- documentation string: what class of departures it can see;
* ``prepare(sample)`` -- returns a fast callable ``f(a) -> float`` that closes
  over everything the permutation does not change;
* ``reference(sample, a)`` -- a deliberately naive recomputation used only by the
  test suite to verify ``prepare``.

Every statistic is oriented so that **larger means more evidence against**
``H0 : S _||_ A | Z``.  The permutation test is exact for *any* statistic, so
this choice affects power only, never validity.

Why the two-implementation split
--------------------------------
``prepare`` caches quantities that are invariant under within-stratum
permutation -- in particular the stratum-by-attribute counts ``n_za``.  That
invariance is a property of the permutation scheme, not of arbitrary
relabellings, so it is unit-tested directly (``tests/test_permutation.py``) and
cross-checked against ``reference`` (``tests/test_statistics.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

from offcriterion.data import FloatArray, IntArray, Sample

PreparedStatistic = Callable[[IntArray], float]

_TINY = 1e-300


def _xlogx(x: FloatArray) -> FloatArray:
    """``x * log(x)`` with the convention ``0 * log 0 = 0``."""
    return np.where(x > 0, x * np.log(np.where(x > 0, x, 1.0)), 0.0)


class Statistic(ABC):
    """Base class for permutation test statistics."""

    name: str = ""
    sensitivity: str = ""

    @abstractmethod
    def prepare(self, sample: Sample) -> PreparedStatistic:
        """Return a callable evaluating the statistic for a given ``a`` vector."""

    @abstractmethod
    def reference(self, sample: Sample, a: IntArray | None = None) -> float:
        """Naive recomputation from scratch.  Correctness oracle for tests."""

    def __call__(self, sample: Sample, a: IntArray | None = None) -> float:
        return self.prepare(sample)(sample.a if a is None else a)


# --------------------------------------------------------------------------
# Contingency-table statistics: sensitive to general distributional dependence
# --------------------------------------------------------------------------


class ConditionalG2(Statistic):
    r"""Conditional likelihood-ratio (G-squared) statistic.

    .. math::
        G^2 = 2 \sum_{z,s,a} n_{zsa}
              \log \frac{n_{zsa}\, n_{z}}{n_{zs}\, n_{za}}
            = 2 n \, \hat{I}(S; A \mid Z)

    Because it compares the full three-way table against the conditional
    independence model, it responds to *any* difference between the conditional
    laws of ``S | A = a, Z = z`` that survives the score discretisation --
    location, scale, skew, tail mass, multimodality.  It does not privilege the
    mean.

    Limitation, stated plainly: "any dependence" here means *any dependence
    visible at the chosen binning*.  Two conditional laws with identical bin
    probabilities are indistinguishable to this statistic.  See
    ``docs/assumptions.md``.

    The plug-in estimator is biased upward in sparse tables.  This does not
    threaten validity: every permuted table has the *same* margins ``n_zs``,
    ``n_za`` and ``n_z`` as the observed one, so the same bias is present in the
    reference distribution and cancels in the comparison.
    """

    name = "conditional_g2"
    sensitivity = "general distributional dependence, at the resolution of the score binning"

    def prepare(self, sample: Sample) -> PreparedStatistic:
        n_z, n_s, n_a = sample.n_z, sample.n_s_bins, sample.n_a
        size = n_z * n_s * n_a

        # Fixed under permutation: (z, s_bin) pairing, hence n_zs and n_z.
        base = (sample.z * n_s + sample.s_bin) * n_a
        counts_zs = np.bincount(sample.z * n_s + sample.s_bin, minlength=n_z * n_s).astype(np.float64)
        counts_z = counts_zs.reshape(n_z, n_s).sum(axis=1)
        # Invariant under *within-stratum* permutation (unit-tested separately).
        counts_za = np.bincount(sample.z * n_a + sample.a, minlength=n_z * n_a).astype(np.float64)

        log_zs = np.where(counts_zs > 0, np.log(np.maximum(counts_zs, _TINY)), 0.0).reshape(n_z, n_s)
        log_za = np.where(counts_za > 0, np.log(np.maximum(counts_za, _TINY)), 0.0).reshape(n_z, n_a)
        log_z = np.where(counts_z > 0, np.log(np.maximum(counts_z, _TINY)), 0.0)

        # offset[z, s, a] = log n_zs + log n_za - log n_z, zeroed on empty margins.
        offset = log_zs[:, :, None] + log_za[:, None, :] - log_z[:, None, None]
        empty = (counts_zs.reshape(n_z, n_s)[:, :, None] <= 0) | (
            counts_za.reshape(n_z, n_a)[:, None, :] <= 0
        )
        offset = np.where(empty, 0.0, offset).ravel()

        def evaluate(a: IntArray) -> float:
            cells = np.bincount(base + a, minlength=size).astype(np.float64)
            return float(2.0 * (_xlogx(cells).sum() - cells @ offset))

        return evaluate

    def reference(self, sample: Sample, a: IntArray | None = None) -> float:
        a = sample.a if a is None else a
        total = 0.0
        for z in range(sample.n_z):
            mz = sample.z == z
            n_zt = int(mz.sum())
            if n_zt == 0:
                continue
            for s in range(sample.n_s_bins):
                n_zs = int(np.sum(mz & (sample.s_bin == s)))
                for g in range(sample.n_a):
                    n_za = int(np.sum(mz & (a == g)))
                    n_zsa = int(np.sum(mz & (sample.s_bin == s) & (a == g)))
                    if n_zsa == 0 or n_zs == 0 or n_za == 0:
                        continue
                    total += n_zsa * np.log((n_zsa * n_zt) / (n_zs * n_za))
        return float(2.0 * total)


class ConditionalMutualInformation(ConditionalG2):
    """Plug-in conditional mutual information ``I(S; A | Z)`` in nats.

    A strictly monotone rescaling of :class:`ConditionalG2` (divide by ``2n``),
    so it induces *identical* permutation p-values.  It is kept as a separate
    entry because it is the interpretable effect size; the equality of p-values
    is asserted in the test suite.
    """

    name = "conditional_mi"
    sensitivity = "identical to conditional_g2; reported on an interpretable (nats) scale"

    def prepare(self, sample: Sample) -> PreparedStatistic:
        inner = super().prepare(sample)
        scale = 1.0 / (2.0 * sample.n)

        def evaluate(a: IntArray) -> float:
            return inner(a) * scale

        return evaluate

    def reference(self, sample: Sample, a: IntArray | None = None) -> float:
        return super().reference(sample, a) / (2.0 * sample.n)


# --------------------------------------------------------------------------
# Mean-oriented baselines.
#
# These are *statistics*, not stand-alone tests.  Running them inside the same
# within-stratum permutation scheme is what makes the comparison table
# interpretable: every column then shares one null, one conditioning set and one
# calibration, so any difference in rejection rate is attributable to the
# statistic rather than to how its reference distribution was obtained.
# --------------------------------------------------------------------------


class StratifiedMeanDisparity(Statistic):
    """Stratum-size-weighted spread of conditional group means.

    .. math::
        T = \\sum_z \\frac{n_z}{n}
            \\left( \\max_a \\bar{S}_{za} - \\min_a \\bar{S}_{za} \\right)

    For binary ``A`` this is the weighted absolute mean difference, i.e. the
    usual aggregate-disparity measure an auditor would reach for first.  It uses
    the *raw* score rather than the binned one, so it is evaluated at its most
    favourable.  By construction it is blind to any departure that leaves all
    conditional means equal.
    """

    name = "stratified_mean_disparity"
    sensitivity = "differences in conditional means only"

    def prepare(self, sample: Sample) -> PreparedStatistic:
        n_z, n_a = sample.n_z, sample.n_a
        zbase = sample.z * n_a
        counts_za = np.bincount(zbase + sample.a, minlength=n_z * n_a).astype(np.float64).reshape(n_z, n_a)
        counts_z = counts_za.sum(axis=1)
        present = counts_za > 0
        weights = counts_z / sample.n
        safe_counts = np.where(present, counts_za, 1.0)
        s_raw = sample.s_raw

        def evaluate(a: IntArray) -> float:
            sums = np.bincount(zbase + a, weights=s_raw, minlength=n_z * n_a).reshape(n_z, n_a)
            means = sums / safe_counts
            hi = np.where(present, means, -np.inf).max(axis=1)
            lo = np.where(present, means, np.inf).min(axis=1)
            spread = np.where(counts_z > 0, hi - lo, 0.0)
            return float(weights @ spread)

        return evaluate

    def reference(self, sample: Sample, a: IntArray | None = None) -> float:
        a = sample.a if a is None else a
        total = 0.0
        for z in range(sample.n_z):
            mz = sample.z == z
            n_zt = int(mz.sum())
            if n_zt == 0:
                continue
            means = [
                float(sample.s_raw[mz & (a == g)].mean())
                for g in range(sample.n_a)
                if np.any(mz & (a == g))
            ]
            total += (n_zt / sample.n) * (max(means) - min(means))
        return float(total)


class StratifiedRegressionLRT(Statistic):
    """Gaussian likelihood-ratio statistic for ``A`` given stratum fixed effects.

    Compares ``S ~ Z`` against ``S ~ Z + A`` (both saturated in ``Z``, and in
    ``Z x A`` for the full model), giving

    .. math:: T = n \\log(\\mathrm{RSS}_0 / \\mathrm{RSS}_1) \\ge 0 .

    This is the regression-based baseline.  Its likelihood is Gaussian with a
    common variance, so it is a *mean* comparison by construction: it has no
    term that can respond to a difference in conditional variance or shape.

    Reported here as a permutation statistic.  Its asymptotic F-calibrated
    counterpart lives in :mod:`offcriterion.baselines`.
    """

    name = "stratified_regression_lrt"
    sensitivity = "differences in conditional means only (Gaussian homoscedastic likelihood)"

    def prepare(self, sample: Sample) -> PreparedStatistic:
        n_z, n_a, n = sample.n_z, sample.n_a, sample.n
        zbase = sample.z * n_a
        s_raw = sample.s_raw
        counts_za = np.bincount(zbase + sample.a, minlength=n_z * n_a).astype(np.float64)
        counts_z = counts_za.reshape(n_z, n_a).sum(axis=1)
        safe_za = np.where(counts_za > 0, counts_za, 1.0)

        total_sq = float(np.dot(s_raw, s_raw))
        sums_z = np.bincount(sample.z, weights=s_raw, minlength=n_z)
        safe_z = np.where(counts_z > 0, counts_z, 1.0)
        rss_null = total_sq - float(np.sum(sums_z**2 / safe_z))
        rss_null = max(rss_null, _TINY)

        def evaluate(a: IntArray) -> float:
            sums = np.bincount(zbase + a, weights=s_raw, minlength=n_z * n_a)
            rss_full = total_sq - float(np.sum(sums**2 / safe_za))
            rss_full = max(rss_full, _TINY)
            return float(n * np.log(rss_null / rss_full))

        return evaluate

    def reference(self, sample: Sample, a: IntArray | None = None) -> float:
        a = sample.a if a is None else a
        rss_null = 0.0
        rss_full = 0.0
        for z in range(sample.n_z):
            mz = sample.z == z
            if not np.any(mz):
                continue
            s_z = sample.s_raw[mz]
            rss_null += float(np.sum((s_z - s_z.mean()) ** 2))
            for g in range(sample.n_a):
                cell = mz & (a == g)
                if np.any(cell):
                    s_cell = sample.s_raw[cell]
                    rss_full += float(np.sum((s_cell - s_cell.mean()) ** 2))
        return float(sample.n * np.log(max(rss_null, _TINY) / max(rss_full, _TINY)))


STATISTICS: dict[str, Statistic] = {
    stat.name: stat
    for stat in (
        ConditionalG2(),
        ConditionalMutualInformation(),
        StratifiedMeanDisparity(),
        StratifiedRegressionLRT(),
    )
}

#: Statistics reported in the headline comparison table, in column order.
DEFAULT_STATISTICS: tuple[str, ...] = (
    "conditional_g2",
    "stratified_mean_disparity",
    "stratified_regression_lrt",
)


def get_statistic(name: str) -> Statistic:
    try:
        return STATISTICS[name]
    except KeyError:
        raise KeyError(f"unknown statistic {name!r}; available: {sorted(STATISTICS)}") from None
