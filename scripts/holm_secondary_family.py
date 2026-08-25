"""Parts 5-6: preregistered Holm correction over the secondary confirmatory
family (size 3) and the four-row primary+secondary comparison table.

The Holm family is exactly the three preregistered secondary tests
(config: multiplicity.secondary_confirmatory_family).  The primary is
preregistered separately as the single primary test and is NOT in the
family; its row appears in the table for comparison only.

Writes results/secondary_confirmatory_summary.json and .md.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

CELLS = [  # frozen family order (prereg section 11)
    ("haiku_plain", "Claude Haiku 4.5, plain rubric"),
    ("gemini_plain", "Gemini 3.7 Flash, plain rubric"),
    ("gpt_ignore", "GPT-5.4-mini, ignore-demographics rubric"),
]
ALPHA = 0.05


def holm(pvals: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, preserving input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def row(report: dict, summary: dict) -> dict:
    diag = report["descriptive_diagnostics"]
    return {
        "N": report["n_analysed"],
        "ELL_N": report["n_ell"],
        "informative_strata": report["n_informative_strata"],
        "conditional_G2": round(report["primary_test"]["observed"], 2),
        "raw_p": report["primary_test"]["p_value"],
        "mean_disparity_stat": round(
            report["permutation_calibrated_baselines"]["stratified_mean_disparity"]["observed"], 4),
        "mean_disparity_p": report["permutation_calibrated_baselines"]["stratified_mean_disparity"]["p_value"],
        "regression_lrt_stat": round(
            report["permutation_calibrated_baselines"]["stratified_regression_lrt"]["observed"], 2),
        "regression_lrt_p": report["permutation_calibrated_baselines"]["stratified_regression_lrt"]["p_value"],
        "conditional_mean_difference": diag["weighted_mean_difference"],
        "P(S>=4)_conditional_shift": diag["weighted_cumulative_shift"]["P(S>=4)"],
        "cumulative_shift_profile": diag["weighted_cumulative_shift"],
        "variance_difference": diag["weighted_variance_difference"],
        "score_distribution_by_ell": report["score_distribution_by_ell"],
        "technical_exclusions": summary["n_technical_failures"],
        "invalid_responses": summary["n_invalid_responses"],
        "input_tokens": summary["input_tokens"],
        "output_tokens": summary["output_tokens"],
        "thinking_tokens": summary.get("thinking_tokens", 0),
        "cost_usd": summary["actual_cost_usd"],
    }


def main() -> None:
    primary = json.loads((RESULTS / "primary_analysis.json").read_text())
    primary_summary = json.loads(
        (ROOT / "data" / "scoring" / "primary" / "stage_d_summary.json").read_text())

    rows = {"PRIMARY: GPT-5.4-mini, plain rubric": row(primary, primary_summary)}
    family = []
    for cell, label in CELLS:
        rep = json.loads((RESULTS / f"secondary_{cell}_analysis.json").read_text())
        summ = json.loads(
            (ROOT / "data" / "scoring" / f"secondary_{cell}" /
             "stage_d_summary.json").read_text())
        rows[label] = row(rep, summ)
        family.append((label, rep["primary_test"]["p_value"]))

    raw_ps = [p for _, p in family]
    adj_ps = holm(raw_ps)
    holm_table = {
        label: {
            "raw_p": p,
            "holm_adjusted_p": round(a, 4),
            "reject_at_familywise_alpha_0.05": bool(a <= ALPHA),
        }
        for (label, p), a in zip(family, adj_ps)
    }
    for label in rows:
        if label in holm_table:
            rows[label]["holm_adjusted_p"] = holm_table[label]["holm_adjusted_p"]
            rows[label]["reject_holm_0.05"] = holm_table[label]["reject_at_familywise_alpha_0.05"]

    out = {
        "family": "preregistered secondary confirmatory family (m=3, Holm, alpha=0.05)",
        "note": ("the primary test is preregistered separately and is NOT a "
                 "member of this Holm family; it appears in the table for "
                 "comparison only"),
        "holm": holm_table,
        "comparison_table": rows,
        "additional_api_cost_usd_secondary_total": round(
            sum(rows[label]["cost_usd"] for _, label in CELLS), 2),
    }
    (RESULTS / "secondary_confirmatory_summary.json").write_text(
        json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
