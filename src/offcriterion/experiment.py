"""Repeated-simulation driver.

Structure of one replicate
--------------------------
1. Draw a synthetic sample from a scenario.
2. Discretise the score from ``(s, z)`` alone -- before any permutation exists.
3. Run every permutation statistic on **one shared set of permutation draws**,
   so the columns are paired rather than independently noisy.
4. Run the non-permutation baselines on the same sample.

Determinism
-----------
Every replicate's data seed and permutation seed are derived from the root seed
and the replicate's *position* via ``SeedSequence`` spawn keys, not from a
running counter.  Results are therefore identical regardless of how many worker
processes are used, or in what order tasks complete.
"""

from __future__ import annotations

import json
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from offcriterion.baselines import BASELINE_NULLS, BASELINES
from offcriterion.discretize import BinningStrategy, discretize
from offcriterion.permutation import permutation_test
from offcriterion.scenarios import SCENARIO_ORDER, get_scenario
from offcriterion.statistics import DEFAULT_STATISTICS

REPLICATE_FIELDS: tuple[str, ...] = (
    "scenario",
    "n",
    "replicate",
    "method",
    "calibration",
    "p_value",
    "observed",
    "n_strata",
    "n_usable_strata",
    "n_score_bins",
)

RATE_FIELDS: tuple[str, ...] = (
    "scenario",
    "null_status",
    "n",
    "method",
    "calibration",
    "n_replicates",
    "n_rejections",
    "rejection_rate",
    "ci_low",
    "ci_high",
)


@dataclass(frozen=True)
class ExperimentConfig:
    """Everything needed to reproduce a full synthetic experiment."""

    scenarios: tuple[str, ...] = SCENARIO_ORDER
    sample_sizes: tuple[int, ...] = (200, 500, 2000)
    n_replicates: int = 1000
    n_permutations: int = 999
    alpha: float = 0.05
    n_score_bins: int = 8
    binning: BinningStrategy = "global_quantile"
    statistics: tuple[str, ...] = DEFAULT_STATISTICS
    baselines: tuple[str, ...] = tuple(BASELINES)
    root_seed: int = 20240817
    n_workers: int = 0  # 0 => os default
    chunk_size: int = 25

    def to_dict(self) -> dict[str, object]:
        payload = dict(asdict(self))
        payload["baseline_nulls"] = {k: BASELINE_NULLS[k] for k in self.baselines}
        return payload


def _seed(config: ExperimentConfig, scenario_index: int, size_index: int, replicate: int, slot: int) -> np.random.Generator:
    """Position-addressed, order-independent generator."""
    sequence = np.random.SeedSequence(
        entropy=config.root_seed, spawn_key=(scenario_index, size_index, replicate, slot)
    )
    return np.random.default_rng(sequence)


def run_replicate(
    config: ExperimentConfig,
    scenario_name: str,
    n: int,
    replicate: int,
) -> list[dict[str, object]]:
    """Run one replicate and return its rows in long format."""
    scenario_index = config.scenarios.index(scenario_name)
    size_index = config.sample_sizes.index(n)
    scenario = get_scenario(scenario_name)

    raw = scenario(n, _seed(config, scenario_index, size_index, replicate, 0))
    sample = discretize(raw, n_bins=config.n_score_bins, strategy=config.binning)

    results = permutation_test(
        sample,
        config.statistics,
        config.n_permutations,
        _seed(config, scenario_index, size_index, replicate, 1),
    )

    rows: list[dict[str, object]] = []
    for name in config.statistics:
        res = results[name]
        rows.append(
            {
                "scenario": scenario_name,
                "n": n,
                "replicate": replicate,
                "method": name,
                "calibration": "stratified_permutation",
                "p_value": res.p_value,
                "observed": res.observed,
                "n_strata": res.n_strata,
                "n_usable_strata": res.n_usable_strata,
                "n_score_bins": sample.n_s_bins,
            }
        )
    for name in config.baselines:
        rows.append(
            {
                "scenario": scenario_name,
                "n": n,
                "replicate": replicate,
                "method": name,
                "calibration": "asymptotic",
                "p_value": float(BASELINES[name](sample)),
                "observed": None,  # not a permutation statistic; NaN would break row equality
                "n_strata": results[config.statistics[0]].n_strata,
                "n_usable_strata": results[config.statistics[0]].n_usable_strata,
                "n_score_bins": sample.n_s_bins,
            }
        )
    return rows


def _run_chunk(payload: tuple[ExperimentConfig, str, int, tuple[int, ...]]) -> list[dict[str, object]]:
    config, scenario_name, n, replicates = payload
    rows: list[dict[str, object]] = []
    for replicate in replicates:
        rows.extend(run_replicate(config, scenario_name, n, replicate))
    return rows


def _chunks(config: ExperimentConfig) -> list[tuple[ExperimentConfig, str, int, tuple[int, ...]]]:
    tasks = []
    for scenario_name in config.scenarios:
        for n in config.sample_sizes:
            for start in range(0, config.n_replicates, config.chunk_size):
                block = tuple(range(start, min(start + config.chunk_size, config.n_replicates)))
                tasks.append((config, scenario_name, n, block))
    return tasks


def run_experiment(
    config: ExperimentConfig, *, progress: bool = True
) -> list[dict[str, object]]:
    """Run every (scenario, sample size, replicate) cell and return all rows."""
    tasks = _chunks(config)
    rows: list[dict[str, object]] = []

    if config.n_workers == 1:
        for index, task in enumerate(tasks, start=1):
            rows.extend(_run_chunk(task))
            if progress:
                _report(index, len(tasks))
    else:
        workers = config.n_workers if config.n_workers > 0 else None
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for index, chunk_rows in enumerate(pool.map(_run_chunk, tasks), start=1):
                rows.extend(chunk_rows)
                if progress:
                    _report(index, len(tasks))
    if progress:
        print()

    rows.sort(key=lambda r: (str(r["scenario"]), int(r["n"]), int(r["replicate"]), str(r["method"])))
    return rows


def _report(done: int, total: int) -> None:
    print(f"\r  {done}/{total} chunks", end="", flush=True)


def wilson_interval(successes: int, trials: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Used instead of a normal approximation because rejection rates near the
    boundaries (a well-calibrated test at alpha = 0.05, or a powerful test near
    1.0) are exactly where the Wald interval misbehaves.
    """
    if trials == 0:
        return (float("nan"), float("nan"))
    from scipy import stats

    z = float(stats.norm.isf(alpha / 2.0))
    phat = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (phat + z * z / (2.0 * trials)) / denominator
    half = (z / denominator) * math.sqrt(phat * (1.0 - phat) / trials + z * z / (4.0 * trials * trials))
    low = 0.0 if successes == 0 else max(0.0, centre - half)
    high = 1.0 if successes == trials else min(1.0, centre + half)
    return (low, high)


def aggregate(
    rows: Iterable[dict[str, object]], config: ExperimentConfig
) -> list[dict[str, object]]:
    """Collapse replicate p-values into rejection rates with Wilson intervals."""
    from offcriterion.scenarios import get_scenario

    buckets: dict[tuple[str, int, str, str], list[float]] = {}
    for row in rows:
        key = (str(row["scenario"]), int(row["n"]), str(row["method"]), str(row["calibration"]))
        buckets.setdefault(key, []).append(float(row["p_value"]))

    methods = list(config.statistics) + list(config.baselines)
    out: list[dict[str, object]] = []
    for scenario_name in config.scenarios:
        for n in config.sample_sizes:
            for method in methods:
                for calibration in ("stratified_permutation", "asymptotic"):
                    key = (scenario_name, n, method, calibration)
                    if key not in buckets:
                        continue
                    values = np.asarray(buckets[key])
                    rejections = int(np.count_nonzero(values <= config.alpha))
                    low, high = wilson_interval(rejections, values.size, config.alpha)
                    out.append(
                        {
                            "scenario": scenario_name,
                            "null_status": get_scenario(scenario_name).null_status,
                            "n": n,
                            "method": method,
                            "calibration": calibration,
                            "n_replicates": values.size,
                            "n_rejections": rejections,
                            "rejection_rate": rejections / values.size,
                            "ci_low": low,
                            "ci_high": high,
                        }
                    )
    return out
