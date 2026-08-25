"""Publication-ready tables built from saved results.

Tables are rendered from ``rejection_rates.csv`` rather than from in-memory
state, so the reporting step can be re-run without re-running the simulation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from offcriterion.storage import read_csv

DISPLAY_NAMES: dict[str, str] = {
    "conditional_g2": "Proposed (cond. G^2)",
    "conditional_mi": "Conditional MI",
    "stratified_mean_disparity": "Mean disparity",
    "stratified_regression_lrt": "Regression LRT",
    "marginal_mean_ttest": "Marginal t-test*",
    "stratified_regression_ftest": "Regression F (asymp.)",
}

NULL_LABELS: dict[str, str] = {
    "true": "H0 true",
    "false": "H0 false",
    "not guaranteed": "H0 not guaranteed",
}

FOOTNOTE = (
    "* The marginal t-test conditions on nothing and therefore tests S _||_ A, not the audit\n"
    "  null S _||_ A | Z. Its rejections in the conditional-null scenarios are correct answers\n"
    "  to a different question, not Type I errors of the audit. It is shown to make the cost of\n"
    "  skipping the conditioning step visible."
)


def _label(method: str) -> str:
    return DISPLAY_NAMES.get(method, method)


def _cell(row: dict[str, str], *, with_ci: bool) -> str:
    rate = float(row["rejection_rate"])
    if not with_ci:
        return f"{rate:.3f}"
    return f"{rate:.3f} [{float(row['ci_low']):.3f}, {float(row['ci_high']):.3f}]"


def _render_markdown(header: Sequence[str], body: Sequence[Sequence[str]]) -> str:
    widths = [
        max(len(str(header[i])), *(len(str(r[i])) for r in body)) if body else len(str(header[i]))
        for i in range(len(header))
    ]
    def line(cells: Sequence[str]) -> str:
        return "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    rule = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([line(header), rule, *(line(r) for r in body)])


def _render_latex(header: Sequence[str], body: Sequence[Sequence[str]], caption: str) -> str:
    def escape(text: str) -> str:
        return str(text).replace("_", r"\_").replace("^", r"\^{}").replace("%", r"\%")

    spec = "l" * 2 + "r" * (len(header) - 2)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\begin{{tabular}}{{{spec}}}",
        r"\toprule",
        " & ".join(escape(h) for h in header) + r" \\",
        r"\midrule",
    ]
    lines += [" & ".join(escape(c) for c in row) + r" \\" for row in body]
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        rf"\caption{{{escape(caption)}}}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def _order(rows: Iterable[dict[str, str]], key: str) -> list[str]:
    seen: list[str] = []
    for row in rows:
        if row[key] not in seen:
            seen.append(row[key])
    return seen


def main_table(
    rows: Sequence[dict[str, str]], *, n: int, alpha: float = 0.05, with_ci: bool = True
) -> tuple[list[str], list[list[str]], str]:
    """Six scenarios x methods, at one sample size."""
    subset = [r for r in rows if int(r["n"]) == n]
    methods = _order(rows, "method")
    header = ["Scenario", "Null"] + [_label(m) for m in methods]
    body: list[list[str]] = []
    for scenario in _order(rows, "scenario"):
        by_method = {r["method"]: r for r in subset if r["scenario"] == scenario}
        if not by_method:
            continue
        null_label = NULL_LABELS.get(by_method[methods[0]]["null_status"], "?")
        body.append(
            [scenario, null_label]
            + [_cell(by_method[m], with_ci=with_ci) if m in by_method else "-" for m in methods]
        )
    caption = (
        f"Empirical rejection rates at alpha = {alpha} over "
        f"{subset[0]['n_replicates'] if subset else '?'} replicates, n = {n}. "
        "Brackets give Wilson 95% intervals."
    )
    return header, body, caption


def by_sample_size_table(
    rows: Sequence[dict[str, str]], *, alpha: float = 0.05
) -> tuple[list[str], list[list[str]], str]:
    """Scenario x sample size, to separate calibration from power."""
    methods = _order(rows, "method")
    header = ["Scenario", "n"] + [_label(m) for m in methods]
    body: list[list[str]] = []
    for scenario in _order(rows, "scenario"):
        for size in sorted({int(r["n"]) for r in rows}):
            by_method = {
                r["method"]: r for r in rows if r["scenario"] == scenario and int(r["n"]) == size
            }
            if not by_method:
                continue
            body.append(
                [scenario, str(size)]
                + [_cell(by_method[m], with_ci=False) if m in by_method else "-" for m in methods]
            )
    caption = f"Empirical rejection rates at alpha = {alpha} by sample size."
    return header, body, caption


def render_report(rows: Sequence[dict[str, str]], *, alpha: float = 0.05) -> tuple[str, str]:
    """Return ``(markdown, latex)`` for the full report."""
    sizes = sorted({int(r["n"]) for r in rows})
    header_a, body_a, caption_a = main_table(rows, n=sizes[-1], alpha=alpha)
    header_b, body_b, caption_b = by_sample_size_table(rows, alpha=alpha)

    markdown = "\n".join(
        [
            "# OffCriterion: synthetic validation results",
            "",
            f"Null hypothesis under test: `H0: S _||_ A | Z`. Significance level alpha = {alpha}.",
            "",
            f"## Table 1. Rejection rates at n = {sizes[-1]}",
            "",
            _render_markdown(header_a, body_a),
            "",
            caption_a,
            "",
            FOOTNOTE,
            "",
            "## Table 2. Rejection rates by sample size",
            "",
            _render_markdown(header_b, body_b),
            "",
            caption_b,
            "",
        ]
    )
    latex = "\n\n".join(
        [
            _render_latex(header_a, body_a, caption_a),
            _render_latex(header_b, body_b, caption_b),
        ]
    )
    return markdown, latex


def render_report_from_file(path: Path, *, alpha: float = 0.05) -> tuple[str, str]:
    return render_report(read_csv(path), alpha=alpha)
