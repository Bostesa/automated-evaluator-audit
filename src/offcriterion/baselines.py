"""Baselines that are *not* calibrated by the stratified permutation scheme.

These exist to make one point precise.  The headline table compares statistics
that all share a single null, a single conditioning set and a single calibration
(see :mod:`offcriterion.statistics`), so differences there are attributable to
the statistic alone.  The baselines here instead vary the *null being tested* and
the *calibration route*:

``marginal_mean_ttest``
    Ignores ``Z`` entirely.  It tests ``S _||_ A``, a different and much stronger
    null.  In the confounded scenarios it rejects at very high rates, which is
    correct for the question it asks and useless for the question an auditor
    asks.  Its rejections must never be read as Type I error of the conditional
    test.

``stratified_regression_ftest``
    The same statistic as
    :class:`~offcriterion.statistics.StratifiedRegressionLRT` but calibrated by
    the asymptotic F distribution rather than by permutation.  Comparing the two
    isolates the effect of calibration: any discrepancy under a true conditional
    null is a failure of the Gaussian/large-sample approximation, not of the
    statistic.

Both return a p-value directly.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy import stats

from offcriterion.data import Sample

BaselineFn = Callable[[Sample], float]


def marginal_mean_ttest(sample: Sample) -> float:
    """Two-sided Welch t-test of the raw score across attribute groups, ignoring ``Z``.

    Defined for binary ``A``.  For more levels this falls back to a one-way
    Welch ANOVA.  Returns 1.0 when a group is too small to admit a variance.
    """
    groups = [sample.s_raw[sample.a == g] for g in range(sample.n_a)]
    groups = [g for g in groups if g.size >= 2]
    if len(groups) < 2:
        return 1.0
    if len(groups) == 2:
        result = stats.ttest_ind(groups[0], groups[1], equal_var=False)
    else:
        result = stats.alexandergovern(*groups)
    p = float(np.atleast_1d(result.pvalue)[0])
    return 1.0 if not np.isfinite(p) else p


def stratified_regression_ftest(sample: Sample) -> float:
    """Asymptotic F-test for ``A`` in a saturated stratum fixed-effects model.

    Compares ``S ~ Z`` (stratum means) against ``S ~ Z * A`` (stratum-by-attribute
    cell means).  Degrees of freedom count only cells that are actually occupied,
    which matters once strata get sparse.
    """
    rss_null = 0.0
    rss_full = 0.0
    n_strata_used = 0
    n_cells_used = 0

    for z in range(sample.n_z):
        mz = sample.z == z
        n_z = int(mz.sum())
        if n_z == 0:
            continue
        n_strata_used += 1
        s_z = sample.s_raw[mz]
        rss_null += float(np.sum((s_z - s_z.mean()) ** 2))
        for g in range(sample.n_a):
            cell = mz & (sample.a == g)
            if np.any(cell):
                n_cells_used += 1
                s_cell = sample.s_raw[cell]
                rss_full += float(np.sum((s_cell - s_cell.mean()) ** 2))

    df_num = n_cells_used - n_strata_used
    df_den = sample.n - n_cells_used
    if df_num <= 0 or df_den <= 0 or rss_full <= 0.0:
        return 1.0

    f_stat = ((rss_null - rss_full) / df_num) / (rss_full / df_den)
    if not np.isfinite(f_stat) or f_stat < 0.0:
        return 1.0
    return float(stats.f.sf(f_stat, df_num, df_den))


BASELINES: dict[str, BaselineFn] = {
    "marginal_mean_ttest": marginal_mean_ttest,
    "stratified_regression_ftest": stratified_regression_ftest,
}

#: What null each baseline actually tests -- reproduced in the output tables so
#: the columns cannot be misread.
BASELINE_NULLS: dict[str, str] = {
    "marginal_mean_ttest": "S _||_ A  (unconditional; NOT the audit null)",
    "stratified_regression_ftest": "S _||_ A | Z  (audit null, asymptotic calibration)",
}
