"""POST-HOC Stage 5: judge-vs-human alignment characterization (descriptive).

Frozen plan section 5.2.  Four cells; versions A (all own valid obs) and
B (complete-case intersection across all four cells).  No hypothesis tests.
"""
from __future__ import annotations

import json
import sys
from math import log2
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results" / "posthoc"

from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.storage import RawScoreStore

CELLS = {
    "GPT-5.4-mini plain": ("primary", "gpt-5.4-mini-2026-03-17", "plain"),
    "Claude Haiku 4.5 plain": ("secondary_haiku_plain", "claude-haiku-4-5-20251001", "plain"),
    "Gemini 3.7 Flash plain": ("secondary_gemini_plain", "gemini-3.7-flash", "plain"),
    "GPT-5.4-mini ignore-demographics": ("secondary_gpt_ignore", "gpt-5.4-mini-2026-03-17", "ignore_demographics"),
}


def load(store_dir: str, judge: str, condition: str) -> dict[str, int]:
    store = RawScoreStore(ROOT / "data" / "scoring" / store_dir)
    out: dict[str, int] = {}
    for rec in store.read(judge, condition):
        try:
            out[rec["essay_id_comp"]] = parse_score(rec["raw_response"])
        except ParseError:
            pass
    return out


def qwk(y: np.ndarray, s: np.ndarray, k: int = 6) -> float:
    o = np.zeros((k, k))
    for yi, si in zip(y, s):
        o[yi - 1, si - 1] += 1
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    e = np.outer(o.sum(1), o.sum(0)) / o.sum()
    return float(1 - (w * o).sum() / (w * e).sum())


def metrics(y: np.ndarray, s: np.ndarray) -> dict:
    dist = np.bincount(s, minlength=7)[1:]
    p = dist / dist.sum()
    nz = p[p > 0]
    H = float(-(nz * np.log2(nz)).sum())
    top2 = float(np.sort(p)[-2:].sum())
    ys, ss = pd.Series(y), pd.Series(s)
    return {
        "N": int(len(y)),
        "exact_agreement": round(float((y == s).mean()), 4),
        "within_one": round(float((abs(y - s) <= 1).mean()), 4),
        "MAE": round(float(np.abs(y - s).mean()), 4),
        "RMSE": round(float(np.sqrt(((y - s) ** 2).mean())), 4),
        "spearman": round(float(ys.corr(ss, method="spearman")), 4),
        "pearson": round(float(ys.corr(ss)), 4),
        "QWK": round(qwk(y, s), 4),
        "judge_distribution_1to6": dist.tolist(),
        "human_distribution_1to6": np.bincount(y, minlength=7)[1:].tolist(),
        "compression": {
            "entropy_bits": round(H, 4),
            "effective_categories_2^H": round(2 ** H, 2),
            "fraction_in_top2_categories": round(top2, 4),
            "min_awarded": int(s.min()), "max_awarded": int(s.max()),
        },
    }


def confusion(y: np.ndarray, s: np.ndarray) -> list[list[int]]:
    m = np.zeros((6, 6), dtype=int)
    for yi, si in zip(y, s):
        m[yi - 1, si - 1] += 1
    return m.tolist()


def main() -> None:
    lvl = pd.read_csv(ROOT / "data/persuade/persuade_essay_level.csv",
                      usecols=["essay_id_comp", "holistic_essay_score"]
                      ).set_index("essay_id_comp").holistic_essay_score
    scores = {label: load(*spec) for label, spec in CELLS.items()}
    common = set.intersection(*(set(v) for v in scores.values()))

    report = {"label": "POST-HOC descriptive alignment; frozen plan section 5.2; "
                       "human score is a benchmark reference, not ground truth",
              "complete_case_intersection_N": len(common),
              "version_A_all_own_valid": {}, "version_B_intersection": {},
              "confusion_matrices_version_A_rows_human_1to6_cols_judge_1to6": {}}
    for label, sc in scores.items():
        ids = sorted(sc)
        y = lvl.loc[ids].to_numpy(dtype=int)
        s = np.array([sc[i] for i in ids])
        report["version_A_all_own_valid"][label] = metrics(y, s)
        report["confusion_matrices_version_A_rows_human_1to6_cols_judge_1to6"][label] = confusion(y, s)
        ids_b = sorted(common)
        yb = lvl.loc[ids_b].to_numpy(dtype=int)
        sb = np.array([sc[i] for i in ids_b])
        report["version_B_intersection"][label] = metrics(yb, sb)

    (OUT / "validity_alignment.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("complete_case_intersection_N",)}, indent=2))
    for label, m in report["version_B_intersection"].items():
        print(label, "->", {k: m[k] for k in ("exact_agreement", "within_one", "MAE", "spearman", "QWK")},
              "compression:", m["compression"])


if __name__ == "__main__":
    main()
