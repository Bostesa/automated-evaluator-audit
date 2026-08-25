"""Command line entry point.

    offcriterion run                # full synthetic experiment + tables
    offcriterion run --quick        # fast smoke configuration
    offcriterion tables             # re-render tables from saved results
    offcriterion diagnostics        # population CMI and conditional moments

``run`` is the single command that reproduces everything in the README.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

from offcriterion.diagnostics import conditional_moments, population_conditional_mi
from offcriterion.experiment import (
    RATE_FIELDS,
    REPLICATE_FIELDS,
    ExperimentConfig,
    aggregate,
    run_experiment,
)
from offcriterion.scenarios import SCENARIO_ORDER, get_scenario
from offcriterion.storage import write_csv, write_json, write_text
from offcriterion.tables import render_report, render_report_from_file

DEFAULT_OUT = Path("results")


def _build_config(args: argparse.Namespace) -> ExperimentConfig:
    config = ExperimentConfig(
        n_replicates=args.replicates,
        n_permutations=args.permutations,
        sample_sizes=tuple(args.sample_sizes),
        alpha=args.alpha,
        n_score_bins=args.bins,
        binning=args.binning,
        root_seed=args.seed,
        n_workers=args.workers,
    )
    if args.quick:
        config = replace(config, n_replicates=100, n_permutations=199, sample_sizes=(200, 1000))
    return config


def _diagnostics_payload(config: ExperimentConfig) -> dict[str, object]:
    payload: dict[str, object] = {}
    for name in config.scenarios:
        scenario = get_scenario(name)
        diagnostic = population_conditional_mi(scenario, n_bins=config.n_score_bins)
        payload[name] = {
            "description": scenario.description,
            "null_status": scenario.null_status,
            "expectation": scenario.expectation,
            "population_conditional_mi": diagnostic.conditional_mi,
            "plug_in_bias_bound": diagnostic.plug_in_bias_bound,
            "detectable_at_this_binning": diagnostic.detectable,
            "conditional_moments": conditional_moments(scenario),
        }
    return payload


def cmd_run(args: argparse.Namespace) -> int:
    config = _build_config(args)
    out = Path(args.out)

    total_cells = len(config.scenarios) * len(config.sample_sizes) * config.n_replicates
    print(f"OffCriterion synthetic experiment")
    print(f"  scenarios     : {len(config.scenarios)}")
    print(f"  sample sizes  : {list(config.sample_sizes)}")
    print(f"  replicates    : {config.n_replicates}  ({total_cells} total fits)")
    print(f"  permutations  : {config.n_permutations}")
    print(f"  alpha         : {config.alpha}")
    print(f"  root seed     : {config.root_seed}")
    print()

    if not args.skip_diagnostics:
        print("Design diagnostics (population CMI at the chosen binning) ...")
        diagnostics = _diagnostics_payload(config)
        write_json(out / "diagnostics.json", diagnostics)
        for name, payload in diagnostics.items():
            cmi = payload["population_conditional_mi"]  # type: ignore[index]
            print(f"  {name:22s} I(S_bin; A | Z) = {float(cmi):.6f}")
        print()

    print("Running replicates ...")
    started = time.perf_counter()
    rows = run_experiment(config)
    elapsed = time.perf_counter() - started
    print(f"  done in {elapsed:.1f} s")

    rates = aggregate(rows, config)
    write_csv(out / "replicates.csv", rows, REPLICATE_FIELDS)
    write_csv(out / "rejection_rates.csv", rates, RATE_FIELDS)
    write_json(out / "rejection_rates.json", rates)
    write_json(out / "config.json", config.to_dict())

    markdown, latex = render_report(
        [{k: str(v) for k, v in row.items()} for row in rates], alpha=config.alpha
    )
    write_text(out / "results.md", markdown)
    write_text(out / "results.tex", latex)

    print(f"\nWrote: {out}/replicates.csv, rejection_rates.csv/.json, config.json, results.md, results.tex\n")
    print(markdown)
    return 0


def cmd_tables(args: argparse.Namespace) -> int:
    out = Path(args.out)
    source = out / "rejection_rates.csv"
    if not source.exists():
        print(f"error: {source} not found; run `offcriterion run` first", file=sys.stderr)
        return 1
    markdown, latex = render_report_from_file(source, alpha=args.alpha)
    write_text(out / "results.md", markdown)
    write_text(out / "results.tex", latex)
    print(markdown)
    return 0


def cmd_diagnostics(args: argparse.Namespace) -> int:
    config = _build_config(args)
    payload = _diagnostics_payload(config)
    write_json(Path(args.out) / "diagnostics.json", payload)
    for name, entry in payload.items():
        print(f"{name}")
        print(f"  null status : {entry['null_status']}")  # type: ignore[index]
        print(f"  population I(S_bin; A | Z) = {float(entry['population_conditional_mi']):.6f}")  # type: ignore[index]
        print(f"  detectable at {config.n_score_bins} bins: {entry['detectable_at_this_binning']}")  # type: ignore[index]
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="offcriterion",
        description="Stratified permutation test for conditional independence (synthetic validation).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--out", default=str(DEFAULT_OUT), help="output directory (default: results)")
        p.add_argument("--alpha", type=float, default=0.05)
        p.add_argument("--bins", type=int, default=8, help="target number of score bins")
        p.add_argument(
            "--binning",
            default="global_quantile",
            choices=("global_quantile", "within_stratum_quantile", "identity"),
        )
        p.add_argument("--replicates", type=int, default=1000)
        p.add_argument("--permutations", type=int, default=999)
        p.add_argument("--sample-sizes", type=int, nargs="+", default=[200, 500, 2000])
        p.add_argument("--seed", type=int, default=20240817)
        p.add_argument("--workers", type=int, default=0, help="0 = all cores, 1 = serial")
        p.add_argument("--quick", action="store_true", help="fast smoke configuration")

    run = sub.add_parser("run", help="run the full synthetic experiment and write tables")
    add_common(run)
    run.add_argument("--skip-diagnostics", action="store_true")
    run.set_defaults(func=cmd_run)

    tables = sub.add_parser("tables", help="re-render tables from saved rejection rates")
    tables.add_argument("--out", default=str(DEFAULT_OUT))
    tables.add_argument("--alpha", type=float, default=0.05)
    tables.set_defaults(func=cmd_tables)

    diagnostics = sub.add_parser("diagnostics", help="population CMI and conditional moments")
    add_common(diagnostics)
    diagnostics.set_defaults(func=cmd_diagnostics)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
