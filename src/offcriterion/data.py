"""Core data containers.

The separation between :class:`RawSample` and :class:`Sample` is deliberate and
load-bearing for the validity of the permutation test.

A :class:`RawSample` is what a generative scenario produces.  A :class:`Sample`
is what the test operates on, and it is built *once*, before any permutation is
drawn.  Discretisation of the score therefore cannot depend on ``A``: it happens
outside the permutation loop, and the loop only ever rewrites the ``a`` array.

See ``docs/assumptions.md`` for why A-free preprocessing is required for
exactness.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]


def _as_codes(x: npt.ArrayLike, name: str) -> IntArray:
    """Coerce to contiguous integer codes ``0..k-1`` and validate."""
    arr = np.asarray(x)
    if not np.issubdtype(arr.dtype, np.integer):
        raise TypeError(f"{name} must be an integer array of category codes, got {arr.dtype}")
    codes = np.ascontiguousarray(arr, dtype=np.int64)
    if codes.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {codes.shape}")
    if codes.size and codes.min() < 0:
        raise ValueError(f"{name} must contain non-negative codes, got min {codes.min()}")
    return codes


@dataclass(frozen=True)
class RawSample:
    """A draw from a generative scenario, before score discretisation.

    Attributes
    ----------
    s:
        Evaluator score.  Continuous or already-discrete; stored as float.
    a:
        Off-criterion attribute, integer codes ``0..n_a-1``.
    z:
        Conditioning variable (the observed intended construct), integer codes
        ``0..n_z-1``.  Discrete by construction so that permutation can be
        carried out exactly within identical strata.
    """

    s: FloatArray
    a: IntArray
    z: IntArray

    def __post_init__(self) -> None:
        s = np.ascontiguousarray(np.asarray(self.s, dtype=np.float64))
        if s.ndim != 1:
            raise ValueError(f"s must be one-dimensional, got shape {s.shape}")
        a = _as_codes(self.a, "a")
        z = _as_codes(self.z, "z")
        if not (s.size == a.size == z.size):
            raise ValueError(f"s, a, z must have equal length, got {s.size}, {a.size}, {z.size}")
        if s.size == 0:
            raise ValueError("sample must be non-empty")
        if not np.all(np.isfinite(s)):
            raise ValueError("s must be finite")
        object.__setattr__(self, "s", s)
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "z", z)

    @property
    def n(self) -> int:
        return int(self.s.size)

    @property
    def n_a(self) -> int:
        return int(self.a.max()) + 1

    @property
    def n_z(self) -> int:
        return int(self.z.max()) + 1


@dataclass(frozen=True)
class Sample:
    """A :class:`RawSample` plus a fixed, A-free discretisation of the score.

    ``s_bin`` is computed once from ``s_raw`` (and optionally ``z``) and is held
    constant for every permutation.  Statistics may use either representation:
    contingency-table statistics use ``s_bin``; mean-oriented baselines use
    ``s_raw`` so that they are evaluated at their most favourable.
    """

    s_raw: FloatArray
    s_bin: IntArray
    a: IntArray
    z: IntArray
    n_s_bins: int
    n_a: int
    n_z: int

    def __post_init__(self) -> None:
        sizes = {self.s_raw.size, self.s_bin.size, self.a.size, self.z.size}
        if len(sizes) != 1:
            raise ValueError("s_raw, s_bin, a and z must have equal length")
        for name, arr, k in (
            ("s_bin", self.s_bin, self.n_s_bins),
            ("a", self.a, self.n_a),
            ("z", self.z, self.n_z),
        ):
            if arr.size and (arr.min() < 0 or arr.max() >= k):
                raise ValueError(f"{name} codes must lie in [0, {k}), got [{arr.min()}, {arr.max()}]")

    @property
    def n(self) -> int:
        return int(self.s_raw.size)


@dataclass(frozen=True)
class Strata:
    """Precomputed positions of each conditioning stratum.

    ``groups[k]`` holds the row indices with ``z == unique_z[k]``.  Permutation
    is applied independently inside each group and never across groups.
    """

    groups: tuple[IntArray, ...]
    unique_z: IntArray

    @classmethod
    def from_codes(cls, z: IntArray) -> "Strata":
        order = np.argsort(z, kind="stable")
        sorted_z = z[order]
        boundaries = np.flatnonzero(np.diff(sorted_z)) + 1
        groups = tuple(
            np.ascontiguousarray(g, dtype=np.int64) for g in np.split(order, boundaries)
        )
        unique_z = np.ascontiguousarray(
            np.concatenate(([sorted_z[0]], sorted_z[boundaries])), dtype=np.int64
        )
        return cls(groups=groups, unique_z=unique_z)

    @property
    def n_strata(self) -> int:
        return len(self.groups)

    def sizes(self) -> IntArray:
        return np.array([g.size for g in self.groups], dtype=np.int64)

    def n_usable(self, a: IntArray) -> int:
        """Number of strata that can actually contribute permutation randomness.

        A stratum contributes nothing unless it holds at least two units *and*
        at least two distinct attribute values.  Such strata add an identical
        constant to the observed and to every permuted statistic, so they are
        harmless for validity but dead weight for power.
        """
        return sum(1 for g in self.groups if g.size >= 2 and np.unique(a[g]).size >= 2)
