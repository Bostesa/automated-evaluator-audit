"""Design diagnostics for the synthetic scenarios.

These answer a question that the rejection-rate table cannot: *is the alternative
we constructed actually visible at the discretisation we chose?*  Without this,
a low rejection rate in the shape-only scenario is ambiguous -- it could mean the
statistic is weak, or it could mean the binning erased the signal, in which case
the "finding" would be an artifact of the experiment design.

``population_conditional_mi`` estimates the population conditional mutual
information ``I(S_binned ; A | Z)`` induced by a scenario at a given binning,
using a very large synthetic reference draw.  It is a Monte Carlo approximation
to a population quantity, not a closed form; at the default reference size the
plug-in bias is several orders of magnitude below the values that matter here.

``conditional_moments`` reports the first four conditional moments per
``(Z, A)`` cell, which is how the shape-only scenario's "matched through three
moments" claim is verified rather than asserted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from offcriterion.discretize import BinningStrategy, discretize
from offcriterion.scenarios import Scenario
from offcriterion.statistics import ConditionalMutualInformation

#: Reference draw size for population quantities.  Large enough that the plug-in
#: bias of the CMI estimator, which is O(cells / (2 * n_ref)), is negligible.
DEFAULT_REFERENCE_N: int = 400_000


@dataclass(frozen=True)
class PopulationDiagnostic:
    scenario: str
    n_bins: int
    reference_n: int
    conditional_mi: float
    plug_in_bias_bound: float

    @property
    def detectable(self) -> bool:
        """Signal comfortably above the estimator's own bias floor."""
        return self.conditional_mi > 10.0 * self.plug_in_bias_bound


def population_conditional_mi(
    scenario: Scenario,
    *,
    n_bins: int = 8,
    reference_n: int = DEFAULT_REFERENCE_N,
    strategy: BinningStrategy = "global_quantile",
    seed: int = 20240817,
) -> PopulationDiagnostic:
    """Estimate ``I(S_binned ; A | Z)`` induced by ``scenario`` at this binning."""
    raw = scenario(reference_n, np.random.default_rng(seed))
    sample = discretize(raw, n_bins=n_bins, strategy=strategy)
    cmi = float(ConditionalMutualInformation()(sample))
    cells = sample.n_z * sample.n_s_bins * sample.n_a
    bias_bound = cells / (2.0 * reference_n)
    return PopulationDiagnostic(
        scenario=scenario.name,
        n_bins=n_bins,
        reference_n=reference_n,
        conditional_mi=cmi,
        plug_in_bias_bound=bias_bound,
    )


def conditional_moments(
    scenario: Scenario,
    *,
    reference_n: int = DEFAULT_REFERENCE_N,
    seed: int = 20240817,
) -> list[dict[str, float]]:
    """First four conditional moments of ``S`` in each ``(Z, A)`` cell."""
    raw = scenario(reference_n, np.random.default_rng(seed))
    rows: list[dict[str, float]] = []
    for z in range(raw.n_z):
        for a in range(raw.n_a):
            cell = (raw.z == z) & (raw.a == a)
            count = int(cell.sum())
            if count < 2:
                continue
            values = raw.s[cell]
            mean = float(values.mean())
            centred = values - mean
            var = float(np.mean(centred**2))
            sd = np.sqrt(var)
            rows.append(
                {
                    "z": float(z),
                    "a": float(a),
                    "n": float(count),
                    "mean": mean,
                    "variance": var,
                    "skewness": float(np.mean((centred / sd) ** 3)),
                    "excess_kurtosis": float(np.mean((centred / sd) ** 4) - 3.0),
                }
            )
    return rows
