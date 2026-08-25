"""A-free discretisation of the evaluator score.

Every function in this module takes ``s`` (and possibly ``z``) and **never**
takes ``a``.  That signature is the enforcement mechanism for the preprocessing
condition required by the permutation argument: because the permutation holds
``s`` and ``z`` fixed and only rewrites ``a``, any transform that is a function
of ``(s, z)`` alone is constant across the permutation distribution and cannot
leak information about the attribute labels.

Pooled sample quantiles are therefore safe *even though they are data-dependent*
-- they are recomputed from nothing that the permutation changes.  Quantiles
computed within levels of ``a`` would not be safe and are not offered here.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from offcriterion.data import FloatArray, IntArray, RawSample, Sample

BinningStrategy = Literal["global_quantile", "within_stratum_quantile", "identity"]


def quantile_bin_edges(s: FloatArray, n_bins: int) -> FloatArray:
    """Interior quantile cut points of ``s``.

    Duplicate cut points (heavy ties in ``s``) are collapsed, so the realised
    number of bins may be smaller than ``n_bins``.  That is a resolution loss,
    not a validity problem.
    """
    if n_bins < 2:
        raise ValueError(f"n_bins must be at least 2, got {n_bins}")
    probs = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    return np.unique(np.quantile(s, probs))


def _relabel(codes: IntArray) -> tuple[IntArray, int]:
    """Map arbitrary integer codes onto contiguous ``0..k-1``."""
    _, inverse = np.unique(codes, return_inverse=True)
    inverse = np.ascontiguousarray(inverse.ravel(), dtype=np.int64)
    return inverse, int(inverse.max()) + 1 if inverse.size else 0


def global_quantile_bins(s: FloatArray, n_bins: int) -> tuple[IntArray, int]:
    """Bin ``s`` at pooled sample quantiles."""
    edges = quantile_bin_edges(s, n_bins)
    codes = np.searchsorted(edges, s, side="right").astype(np.int64)
    return _relabel(codes)


def within_stratum_quantile_bins(
    s: FloatArray, z: IntArray, n_bins: int
) -> tuple[IntArray, int]:
    """Bin ``s`` at quantiles computed separately inside each ``z`` stratum.

    Uses more of the resolution of ``s`` when ``z`` shifts the score
    distribution a lot, at the cost of sparser cells.  Still a function of
    ``(s, z)`` only, so still permutation-safe.
    """
    codes = np.empty(s.size, dtype=np.int64)
    for value in np.unique(z):
        mask = z == value
        edges = quantile_bin_edges(s[mask], n_bins)
        codes[mask] = np.searchsorted(edges, s[mask], side="right")
    return _relabel(codes)


def discretize(
    raw: RawSample,
    *,
    n_bins: int = 8,
    strategy: BinningStrategy = "global_quantile",
) -> Sample:
    """Build a :class:`Sample` from a :class:`RawSample`.

    Parameters
    ----------
    n_bins:
        Target number of score bins.  Ignored for ``strategy="identity"``.
    strategy:
        ``"global_quantile"``   -- pooled quantile cuts (default);
        ``"within_stratum_quantile"`` -- quantile cuts inside each ``z`` level;
        ``"identity"`` -- ``s`` is already discrete; relabel its distinct values.

    Notes
    -----
    The contingency-table statistic is omnibus only *with respect to this
    discretisation*.  Alternatives whose conditional laws differ but induce
    identical bin probabilities are invisible to it.  See ``docs/assumptions.md``.
    """
    if strategy == "global_quantile":
        s_bin, k = global_quantile_bins(raw.s, n_bins)
    elif strategy == "within_stratum_quantile":
        s_bin, k = within_stratum_quantile_bins(raw.s, raw.z, n_bins)
    elif strategy == "identity":
        s_bin, k = _relabel(np.round(raw.s).astype(np.int64))
    else:  # pragma: no cover - guarded by Literal
        raise ValueError(f"unknown binning strategy {strategy!r}")

    return Sample(
        s_raw=raw.s,
        s_bin=s_bin,
        a=raw.a,
        z=raw.z,
        n_s_bins=k,
        n_a=raw.n_a,
        n_z=raw.n_z,
    )
