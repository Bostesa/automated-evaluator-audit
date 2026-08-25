"""Synthetic generative scenarios.

Six scenarios span the cases an auditor needs to distinguish: a true conditional
null, three alternatives that differ in *which moment* carries the dependence,
and two confounded designs that differ only in whether the intended construct is
observed exactly or through a noisy proxy.

Everything here is synthetic.  No real dataset or API is touched anywhere in
this package.

Shared structure
----------------
Scenarios 1-4 use a latent quality level ``Q`` on five levels with
``E[S | Q] = MU_SPACING * (Q - 2)``, and make the attribute depend on ``Q``:

    ``A | Q ~ Bernoulli(sigmoid(GAMMA * (Q - 2)))``

That dependence is deliberate.  If ``A`` were independent of ``Q`` the
conditioning step would be vacuous and the scenarios would not test anything
about *conditional* independence.  It also means ``S`` and ``A`` are strongly
dependent *marginally* in every one of these scenarios, including the null one --
which is exactly what makes the unconditional baselines in
:mod:`offcriterion.baselines` reject in scenario 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from offcriterion.data import IntArray, RawSample

#: Number of levels of the latent construct Q.
N_Q: int = 5
#: Spacing of E[S | Q] across levels of Q.  Kept comparable to the within-level
#: standard deviation so that pooled quantile bins of S retain usable resolution
#: inside each stratum.
MU_SPACING: float = 0.6
#: Strength of the Q -> A dependence in scenarios 1-4.
GAMMA: float = 0.8

NullStatus = str
NULL_TRUE: NullStatus = "true"
NULL_FALSE: NullStatus = "false"
NULL_NOT_GUARANTEED: NullStatus = "not guaranteed"


def _mu(q: IntArray) -> np.ndarray:
    return MU_SPACING * (q.astype(np.float64) - (N_Q - 1) / 2.0)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _draw_q_uniform(n: int, rng: np.random.Generator) -> IntArray:
    return rng.integers(0, N_Q, size=n).astype(np.int64)


def _draw_a_given_q(q: IntArray, rng: np.random.Generator) -> IntArray:
    p = _sigmoid(GAMMA * (q.astype(np.float64) - (N_Q - 1) / 2.0))
    return (rng.random(q.size) < p).astype(np.int64)


@dataclass(frozen=True)
class Scenario:
    """A named generative process plus its ground-truth null status."""

    name: str
    description: str
    null_status: NullStatus
    generate: Callable[[int, np.random.Generator], RawSample] = field(repr=False)
    #: Human-readable note on what the scenario is meant to demonstrate.
    expectation: str = ""

    def __call__(self, n: int, rng: np.random.Generator) -> RawSample:
        return self.generate(n, rng)


# --------------------------------------------------------------------------
# 1. True conditional null
# --------------------------------------------------------------------------


def generate_conditional_null(n: int, rng: np.random.Generator) -> RawSample:
    """``S _||_ A | Q`` holds exactly.  ``S`` and ``A`` are dependent marginally."""
    q = _draw_q_uniform(n, rng)
    a = _draw_a_given_q(q, rng)
    s = _mu(q) + rng.standard_normal(n)
    return RawSample(s=s, a=a, z=q)


# --------------------------------------------------------------------------
# 2. Mean dependence
# --------------------------------------------------------------------------


def make_mean_dependence(delta: float = 0.30) -> Callable[[int, np.random.Generator], RawSample]:
    """``E[S | Q, A] = mu(Q) + delta * A``; conditional variance and shape unchanged."""

    def generate(n: int, rng: np.random.Generator) -> RawSample:
        q = _draw_q_uniform(n, rng)
        a = _draw_a_given_q(q, rng)
        s = _mu(q) + delta * a.astype(np.float64) + rng.standard_normal(n)
        return RawSample(s=s, a=a, z=q)

    return generate


# --------------------------------------------------------------------------
# 3. Variance-only dependence
# --------------------------------------------------------------------------


def make_variance_only(
    sigma_0: float = 1.0, sigma_1: float = 1.6
) -> Callable[[int, np.random.Generator], RawSample]:
    """Equal conditional means, unequal conditional variances.

    ``S | Q, A ~ Normal(mu(Q), sigma_A^2)``.  Every conditional mean matches
    exactly, so a mean-disparity statistic has no signal to find; the dependence
    lives entirely in the second moment.
    """

    def generate(n: int, rng: np.random.Generator) -> RawSample:
        q = _draw_q_uniform(n, rng)
        a = _draw_a_given_q(q, rng)
        sigma = np.where(a == 1, sigma_1, sigma_0)
        s = _mu(q) + sigma * rng.standard_normal(n)
        return RawSample(s=s, a=a, z=q)

    return generate


# --------------------------------------------------------------------------
# 4. Shape-only dependence
# --------------------------------------------------------------------------

#: Component variances of the A = 1 mixture.  With equal mixing weights these
#: give mean 0, variance 1 and skewness 0 -- matching Normal(0, 1) exactly
#: through three moments -- but excess kurtosis 3 * 1.5625 = 4.6875 instead of 3.
_MIX_VAR_LOW: float = 0.25
_MIX_VAR_HIGH: float = 1.75


def generate_shape_only(n: int, rng: np.random.Generator) -> RawSample:
    """Matched conditional mean, variance and skewness; different tail shape.

    ``S | Q, A = 0`` is ``mu(Q) + Normal(0, 1)``.
    ``S | Q, A = 1`` is ``mu(Q) +`` an equal-weight scale mixture of two
    zero-mean normals with variances 0.25 and 1.75.

    The mixture has mean 0, variance ``0.5 * 0.25 + 0.5 * 1.75 = 1`` and, being
    symmetric, skewness 0.  Only the fourth and higher moments differ.  Mean- and
    variance-based comparisons are therefore both powerless here by construction.
    """
    q = _draw_q_uniform(n, rng)
    a = _draw_a_given_q(q, rng)
    noise = rng.standard_normal(n)
    heavy = rng.random(n) < 0.5
    mixture_sd = np.where(heavy, np.sqrt(_MIX_VAR_HIGH), np.sqrt(_MIX_VAR_LOW))
    s = _mu(q) + np.where(a == 1, mixture_sd * noise, noise)
    return RawSample(s=s, a=a, z=q)


# --------------------------------------------------------------------------
# 5. Confounded, true construct observed:  A -> Q -> S
# --------------------------------------------------------------------------

_CONFOUND_P0: float = 0.35
_CONFOUND_DP: float = 0.30


def _draw_confounded_q(n: int, rng: np.random.Generator) -> tuple[IntArray, IntArray]:
    a = (rng.random(n) < 0.5).astype(np.int64)
    p = _CONFOUND_P0 + _CONFOUND_DP * a
    q = rng.binomial(N_Q - 1, p).astype(np.int64)
    return a, q


def generate_confounded_observed(n: int, rng: np.random.Generator) -> RawSample:
    """``A -> Q -> S`` with ``Q`` observed and used as the conditioning variable.

    ``S`` depends on ``A`` only through ``Q``, so ``S _||_ A | Q`` holds exactly
    while ``S`` and ``A`` are strongly dependent marginally.  Conditioning on the
    exact ``Q`` restores the null; this is the scenario that separates a genuine
    conditional test from an aggregate disparity measure.
    """
    a, q = _draw_confounded_q(n, rng)
    s = _mu(q) + rng.standard_normal(n)
    return RawSample(s=s, a=a, z=q)


# --------------------------------------------------------------------------
# 6. Confounded, only a noisy proxy for the construct is observed
# --------------------------------------------------------------------------

#: Fixed, prespecified cut points for the proxy.  Deliberately *not* sample
#: quantiles: with fixed cuts the stratum label is a per-unit function of Y, so
#: the only thing that can break the null here is coarsening of the construct,
#: not data-dependent construction of the strata.
_PROXY_CUTS: tuple[float, ...] = (0.5, 1.5, 2.5, 3.5)


def make_confounded_proxy(tau: float = 1.0) -> Callable[[int, np.random.Generator], RawSample]:
    """``A -> Q -> S`` but conditioning on a discretised noisy measurement of ``Q``.

    We observe ``Y = Q + Normal(0, tau^2)`` and condition on ``Z = bin(Y)``.

    This scenario is intentionally **not** guaranteed to satisfy the null, and it
    is not a stress test of the permutation machinery.  Units sharing a value of
    ``Z`` no longer share a value of ``Q``, so ``P(A | Q)`` varies inside a
    stratum and the exchangeability step of the permutation argument fails --
    that is, ``S _||_ A | Z`` is simply false even though ``S _||_ A | Q`` holds.
    A rejection here is a *correct* rejection of a false null, not a Type I error.

    Setting ``tau = 0`` recovers scenario 5 exactly and is used as a sanity check
    in the test suite.
    """

    def generate(n: int, rng: np.random.Generator) -> RawSample:
        a, q = _draw_confounded_q(n, rng)
        s = _mu(q) + rng.standard_normal(n)
        y = q.astype(np.float64) + tau * rng.standard_normal(n)
        z = np.searchsorted(np.asarray(_PROXY_CUTS), y, side="right").astype(np.int64)
        return RawSample(s=s, a=a, z=z)

    return generate


SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in (
        Scenario(
            name="conditional_null",
            description="S independent of A given Q; A depends on Q, so S and A are dependent marginally.",
            null_status=NULL_TRUE,
            generate=generate_conditional_null,
            expectation="Rejection rate should sit at or below alpha at every sample size.",
        ),
        Scenario(
            name="mean_dependence",
            description="Conditional means differ across A; variance and shape unchanged.",
            null_status=NULL_FALSE,
            generate=make_mean_dependence(),
            expectation="Power should rise with n for every statistic, including the mean baselines.",
        ),
        Scenario(
            name="variance_only",
            description="Conditional means equal, conditional variances differ (1.0 vs 1.6).",
            null_status=NULL_FALSE,
            generate=make_variance_only(),
            expectation="Mean-oriented baselines should stay near alpha; the table statistic should gain power.",
        ),
        Scenario(
            name="shape_only",
            description="Conditional mean, variance and skewness matched; tail shape differs.",
            null_status=NULL_FALSE,
            generate=generate_shape_only,
            expectation="Both mean baselines should stay near alpha; only the table statistic should detect it.",
        ),
        Scenario(
            name="confounded_observed",
            description="A -> Q -> S with Q observed; conditioning on Q.",
            null_status=NULL_TRUE,
            generate=generate_confounded_observed,
            expectation="Nominal Type I error, despite very strong marginal dependence.",
        ),
        Scenario(
            name="confounded_proxy",
            description="A -> Q -> S but conditioning on a discretised noisy proxy Y for Q.",
            null_status=NULL_NOT_GUARANTEED,
            generate=make_confounded_proxy(),
            expectation="Residual dependence from imperfect measurement; rejections here are correct, not Type I errors.",
        ),
    )
}

#: Canonical row order for the results table.
SCENARIO_ORDER: tuple[str, ...] = tuple(SCENARIOS)


def get_scenario(name: str) -> Scenario:
    try:
        return SCENARIOS[name]
    except KeyError:
        raise KeyError(f"unknown scenario {name!r}; available: {sorted(SCENARIOS)}") from None
