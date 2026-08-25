"""Tests of the command-line surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from offcriterion.cli import main
from offcriterion.storage import read_csv, read_json


def test_run_produces_every_machine_readable_artifact(tmp_path: Path) -> None:
    exit_code = main(
        [
            "run",
            "--out", str(tmp_path),
            "--replicates", "4",
            "--permutations", "19",
            "--sample-sizes", "120",
            "--skip-diagnostics",
        ]
    )
    assert exit_code == 0
    for name in ("replicates.csv", "rejection_rates.csv", "rejection_rates.json", "config.json", "results.md", "results.tex"):
        assert (tmp_path / name).exists(), name

    rates = read_csv(tmp_path / "rejection_rates.csv")
    assert {r["scenario"] for r in rates} == {
        "conditional_null", "mean_dependence", "variance_only",
        "shape_only", "confounded_observed", "confounded_proxy",
    }
    for row in read_csv(tmp_path / "replicates.csv"):
        assert 0.0 < float(row["p_value"]) <= 1.0


def test_saved_config_is_enough_to_reproduce_the_run(tmp_path: Path) -> None:
    args = [
        "run", "--out", str(tmp_path), "--replicates", "3", "--permutations", "19",
        "--sample-sizes", "120", "--skip-diagnostics",
    ]
    main(args)
    first = read_csv(tmp_path / "replicates.csv")
    config = read_json(tmp_path / "config.json")
    assert config["root_seed"] == 20240817
    assert config["n_permutations"] == 19
    assert "baseline_nulls" in config

    main(args)
    assert read_csv(tmp_path / "replicates.csv") == first


def test_tables_command_regenerates_from_saved_results(tmp_path: Path) -> None:
    main([
        "run", "--out", str(tmp_path), "--replicates", "3", "--permutations", "19",
        "--sample-sizes", "120", "--skip-diagnostics",
    ])
    (tmp_path / "results.md").unlink()
    assert main(["tables", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "results.md").exists()


def test_tables_command_fails_cleanly_without_results(tmp_path: Path) -> None:
    assert main(["tables", "--out", str(tmp_path)]) == 1


def test_diagnostics_command_reports_population_signal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["diagnostics", "--out", str(tmp_path)]) == 0
    payload = read_json(tmp_path / "diagnostics.json")
    assert payload["shape_only"]["detectable_at_this_binning"] is True
    assert payload["conditional_null"]["detectable_at_this_binning"] is False
