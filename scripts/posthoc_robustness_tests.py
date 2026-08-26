"""POST-HOC Stage 3/4: richer-conditioning G2 robustness tests.

Frozen plan section 5.1.  Plain-rubric cells only.  Z1 and Z2 both passed
the section-4 gates, so both run.  Uses the frozen framework unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results" / "posthoc"

from offcriterion.data import Sample, Strata
from offcriterion.permutation import permutation_test
from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.storage import RawScoreStore

CELLS = [  # (label, store dir, judge id, spawn j, frozen confirmatory Delta_Z0)
    ("GPT-5.4-mini plain", "primary", "gpt-5.4-mini-2026-03-17", 0, -0.3202),
    ("Claude Haiku 4.5 plain", "secondary_haiku_plain", "claude-haiku-4-5-20251001", 1, -0.5982),
    ("Gemini 3.7 Flash plain", "secondary_gemini_plain", "gemini-3.7-flash", 2, -0.4440),
]
PERM_SEED = 427183
B = 999


def load_scores(store_dir: str, judge: str, condition: str = "plain") -> dict[str, int]:
    store = RawScoreStore(ROOT / "data" / "scoring" / store_dir)
    scores: dict[str, int] = {}
    for rec in store.read(judge, condition):
        try:
            scores[rec["essay_id_comp"]] = parse_score(rec["raw_response"])
        except ParseError:
            pass
    return scores


def weighted_diag(s: np.ndarray, a: np.ndarray, z: np.ndarray) -> dict:
    strata = Strata.from_codes(z)
    w_total = 0
    mean_d = 0.0
    cum = np.zeros(5)
    for group in strata.groups:
        a_g, s_g = a[group], s[group]
        if a_g.min() == a_g.max() or group.size < 2:
            continue
        w = group.size
        s1, s0 = s_g[a_g == 1], s_g[a_g == 0]
        mean_d += w * (s1.mean() - s0.mean())
        for j, k in enumerate(range(2, 7)):
            cum[j] += w * ((s1 >= k).mean() - (s0 >= k).mean())
        w_total += w
    return {
        "conditional_mean_difference": round(mean_d / w_total, 4),
        "cumulative_shift": {f"P(S>={k})": round(cum[j] / w_total, 4)
                             for j, k in enumerate(range(2, 7))},
    }


def run_cell(df: pd.DataFrame, zcols: list[str], spawn: tuple[int, int]) -> dict:
    keys = list(map(tuple, df[zcols].to_numpy()))
    code_of = {k: i for i, k in enumerate(sorted(set(map(str, keys))))}
    z = np.asarray([code_of[str(k)] for k in keys], dtype=np.int64)
    s = df.judge_score.to_numpy(dtype=np.int64)
    a = df.ell.to_numpy(dtype=np.int64)
    sample = Sample(s_raw=s.astype(np.float64), s_bin=s - 1, a=a, z=z,
                    n_s_bins=6, n_a=2, n_z=len(code_of))
    rng = np.random.default_rng(np.random.SeedSequence(entropy=PERM_SEED, spawn_key=spawn))
    res = permutation_test(sample, statistic_names=("conditional_g2",),
                           n_permutations=B, rng=rng)["conditional_g2"]
    out = {
        "N": int(sample.n), "ELL_N": int(a.sum()),
        "informative_strata": int(res.n_usable_strata),
        "conditional_G2": round(res.observed, 2),
        "p_value": res.p_value,
    }
    out.update(weighted_diag(s, a, z))
    return out


def main() -> None:
    bins = pd.read_csv(OUT / "strata_bins.csv")
    frozen = json.loads((OUT / "strata_bins_FROZEN.json").read_text())
    assert hashlib.sha256((OUT / "strata_bins.csv").read_bytes()).hexdigest() == frozen["sha256"]
    lvl = pd.read_csv(ROOT / "data/persuade/persuade_essay_level.csv",
                      usecols=["essay_id_comp", "prompt_name", "holistic_essay_score", "ell_status"])
    base = bins.merge(lvl, on="essay_id_comp")
    base["ell"] = (base.ell_status == "Yes").astype(int)

    z_defs = {
        "Z0": ["prompt_name", "holistic_essay_score"],
        "Z1": ["prompt_name", "holistic_essay_score", "qbin"],
        "Z2": ["prompt_name", "holistic_essay_score", "qbin", "lbin"],
    }
    report = {"label": "POST-HOC robustness tests; frozen plan section 5.1; "
                       "no confirmatory status attaches to these p-values",
              "B": B, "permutation_seed": PERM_SEED, "cells": {}}

    for label, store_dir, judge, j, delta_z0_frozen in CELLS:
        scores = load_scores(store_dir, judge)
        df = base[base.essay_id_comp.isin(scores)].copy()
        df["judge_score"] = df.essay_id_comp.map(scores)
        cell = {"frozen_confirmatory_Delta_Z0": delta_z0_frozen}
        for zname, zcols in z_defs.items():
            spawn = {"Z0": (20, j), "Z1": (10, j), "Z2": (11, j)}[zname]
            cell[zname] = run_cell(df, zcols, spawn)
        d0, d1, d2 = (cell[k]["conditional_mean_difference"] for k in ("Z0", "Z1", "Z2"))
        cell["attenuation"] = {
            "Delta_Z0_matched_full_valid_sample": d0,
            "Delta_Z1": d1, "Delta_Z2": d2,
            "attenuation_Z1_minus_Z0": round(d1 - delta_z0_frozen, 4),
            "attenuation_Z2_minus_Z0": round(d2 - delta_z0_frozen, 4),
            "pct_attenuation_Z1": round(100 * (abs(delta_z0_frozen) - abs(d1)) / abs(delta_z0_frozen), 1),
            "pct_attenuation_Z2": round(100 * (abs(delta_z0_frozen) - abs(d2)) / abs(delta_z0_frozen), 1),
        }
        report["cells"][label] = cell
        print(f"done: {label}", file=sys.stderr)

    (OUT / "robustness_tests.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
