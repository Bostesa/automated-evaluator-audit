"""Tests of the experiment driver, aggregation and reporting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from offcriterion.experiment import (
    RATE_FIELDS,
    REPLICATE_FIELDS,
    ExperimentConfig,
    _seed,
    aggregate,
    run_experiment,
    run_replicate,
    wilson_interval,
)
from offcriterion.storage import read_csv, read_json, write_csv, write_json
from offcriterion.tables import render_report

TINY = ExperimentConfig(
    scenarios=("conditional_null", "variance_only"),
    sample_sizes=(120,),
    n_replicates=6,
    n_permutations=49,
    chunk_size=2,
)


# --------------------------------------------------------------------------
# Requirement: identical random seeds reproduce identical results
# --------------------------------------------------------------------------


def test_replicate_is_reproducible() -> None:
    first = run_replicate(TINY, "conditional_null", 120, 0)
    second = run_replicate(TINY, "conditional_null", 120, 0)
    assert first == second


def test_distinct_replicates_are_distinct_draws() -> None:
    first = run_replicate(TINY, "conditional_null", 120, 0)
    second = run_replicate(TINY, "conditional_null", 120, 1)
    assert [r["p_value"] for r in first] != [r["p_value"] for r in second]


def test_seeds_are_position_addressed_not_sequential() -> None:
    """Two cells must not share a stream, and a cell's stream must not move."""
    a = _seed(TINY, 0, 0, 0, 0).standard_normal(5)
    b = _seed(TINY, 0, 0, 0, 0).standard_normal(5)
    c = _seed(TINY, 0, 0, 1, 0).standard_normal(5)
    d = _seed(TINY, 1, 0, 0, 0).standard_normal(5)
    e = _seed(TINY, 0, 0, 0, 1).standard_normal(5)
    assert np.array_equal(a, b)
    for other in (c, d, e):
        assert not np.array_equal(a, other)


def test_results_do_not_depend_on_worker_count() -> None:
    """Parallelism must not perturb the numbers, or reproducibility is a fiction."""
    serial = run_experiment(TINY, progress=False)
    parallel = run_experiment(
        ExperimentConfig(**{**TINY.__dict__, "n_workers": 2}), progress=False
    )
    assert serial == parallel


def test_whole_experiment_is_reproducible_end_to_end() -> None:
    first = run_experiment(TINY, progress=False)
    second = run_experiment(TINY, progress=False)
    assert first == second


def test_changing_the_root_seed_changes_the_results() -> None:
    other = ExperimentConfig(**{**TINY.__dict__, "root_seed": TINY.root_seed + 1})
    assert run_experiment(TINY, progress=False) != run_experiment(other, progress=False)


# --------------------------------------------------------------------------
# Requirement: every reported p-value lies in (0, 1]
# --------------------------------------------------------------------------


def test_every_reported_p_value_is_in_the_open_unit_interval() -> None:
    for row in run_experiment(TINY, progress=False):
        p = float(row["p_value"])
        assert 0.0 < p <= 1.0, row
        if row["calibration"] == "stratified_permutation":
            assert p >= 1.0 / (TINY.n_permutations + 1)


def test_every_configured_method_appears_for_every_cell() -> None:
    rows = run_experiment(TINY, progress=False)
    expected = set(TINY.statistics) | set(TINY.baselines)
    for scenario in TINY.scenarios:
        for replicate in range(TINY.n_replicates):
            present = {
                r["method"]
                for r in rows
                if r["scenario"] == scenario and r["replicate"] == replicate
            }
            assert present == expected


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def test_aggregate_counts_rejections_at_alpha() -> None:
    config = ExperimentConfig(
        scenarios=("conditional_null",),
        sample_sizes=(100,),
        statistics=("conditional_g2",),
        baselines=(),
        alpha=0.05,
    )
    rows = [
        {
            "scenario": "conditional_null",
            "n": 100,
            "replicate": i,
            "method": "conditional_g2",
            "calibration": "stratified_permutation",
            "p_value": p,
        }
        for i, p in enumerate([0.01, 0.05, 0.0500001, 0.2, 0.9])
    ]
    summary = aggregate(rows, config)
    assert len(summary) == 1
    # p = 0.05 rejects (the test is `p <= alpha`); p = 0.0500001 does not.
    assert summary[0]["n_rejections"] == 2
    assert summary[0]["rejection_rate"] == pytest.approx(2 / 5)
    assert summary[0]["null_status"] == "true"


def test_wilson_interval_brackets_the_point_estimate() -> None:
    for successes, trials in [(0, 100), (5, 100), (50, 1000), (1000, 1000)]:
        low, high = wilson_interval(successes, trials)
        assert 0.0 <= low <= successes / trials <= high <= 1.0


def test_wilson_interval_narrows_with_more_trials() -> None:
    narrow = wilson_interval(50, 1000)
    wide = wilson_interval(5, 100)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_wilson_interval_is_undefined_without_trials() -> None:
    low, high = wilson_interval(0, 0)
    assert np.isnan(low) and np.isnan(high)


# --------------------------------------------------------------------------
# Persistence and reporting
# --------------------------------------------------------------------------


def test_results_round_trip_through_csv_and_json(tmp_path: Path) -> None:
    rows = run_experiment(TINY, progress=False)
    rates = aggregate(rows, TINY)

    csv_path = write_csv(tmp_path / "replicates.csv", rows, REPLICATE_FIELDS)
    rate_path = write_csv(tmp_path / "rejection_rates.csv", rates, RATE_FIELDS)
    json_path = write_json(tmp_path / "rejection_rates.json", rates)

    reloaded = read_csv(csv_path)
    assert len(reloaded) == len(rows)
    assert float(reloaded[0]["p_value"]) == pytest.approx(float(rows[0]["p_value"]))
    assert len(read_csv(rate_path)) == len(rates)
    assert len(read_json(json_path)) == len(rates)


def test_report_contains_every_scenario_and_method(tmp_path: Path) -> None:
    rates = aggregate(run_experiment(TINY, progress=False), TINY)
    markdown, latex = render_report([{k: str(v) for k, v in r.items()} for r in rates])
    for scenario in TINY.scenarios:
        assert scenario in markdown
    assert "Proposed (cond. G^2)" in markdown
    assert "Mean disparity" in markdown
    assert r"\begin{tabular}" in latex
    # The footnote that stops the marginal baseline from being misread.
    assert "not the audit" in markdown
