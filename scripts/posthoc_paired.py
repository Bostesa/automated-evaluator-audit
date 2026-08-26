"""POST-HOC Stage 6: paired plain vs ignore-demographics (GPT-5.4-mini).

Frozen plan section 5.3.  D_i = S_ignore - S_plain on the common-pair
sample; Z0 strata; stratified permutation (B=999, two-sided, +1 rule,
spawn (12,0)); stratified bootstrap percentile CI (2000 reps, spawn (12,1)).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results" / "posthoc"

from offcriterion.pipeline.parse import ParseError, parse_score
from offcriterion.pipeline.storage import RawScoreStore

PERM_SEED, B, BOOT = 427183, 999, 2000


def load(store_dir: str, judge: str, condition: str) -> dict[str, int]:
    store = RawScoreStore(ROOT / "data" / "scoring" / store_dir)
    out: dict[str, int] = {}
    for rec in store.read(judge, condition):
        try:
            out[rec["essay_id_comp"]] = parse_score(rec["raw_response"])
        except ParseError:
            pass
    return out


def weighted_gap(vals: np.ndarray, a: np.ndarray, groups: list[np.ndarray]) -> float:
    tot = 0.0
    w_tot = 0
    for g in groups:
        a_g = a[g]
        if a_g.min() == a_g.max() or g.size < 2:
            continue
        v = vals[g]
        tot += g.size * (v[a_g == 1].mean() - v[a_g == 0].mean())
        w_tot += g.size
    return tot / w_tot


def main() -> None:
    plain = load("primary", "gpt-5.4-mini-2026-03-17", "plain")
    ign = load("secondary_gpt_ignore", "gpt-5.4-mini-2026-03-17", "ignore_demographics")
    common = sorted(set(plain) & set(ign))

    lvl = pd.read_csv(ROOT / "data/persuade/persuade_essay_level.csv",
                      usecols=["essay_id_comp", "prompt_name", "holistic_essay_score", "ell_status"])
    df = lvl[lvl.essay_id_comp.isin(common)].sort_values("essay_id_comp").reset_index(drop=True)
    df["s_plain"] = df.essay_id_comp.map(plain)
    df["s_ign"] = df.essay_id_comp.map(ign)
    df["d"] = df.s_ign - df.s_plain
    df["ell"] = (df.ell_status == "Yes").astype(int)

    z_codes = df.groupby(["prompt_name", "holistic_essay_score"], observed=True).ngroup().to_numpy()
    groups = [np.flatnonzero(z_codes == c) for c in np.unique(z_codes)]
    a = df.ell.to_numpy()
    d = df.d.to_numpy(dtype=float)

    delta_plain = weighted_gap(df.s_plain.to_numpy(dtype=float), a, groups)
    delta_ign = weighted_gap(df.s_ign.to_numpy(dtype=float), a, groups)
    T = weighted_gap(d, a, groups)  # == delta_ign - delta_plain on the paired sample

    rng = np.random.default_rng(np.random.SeedSequence(entropy=PERM_SEED, spawn_key=(12, 0)))
    null = np.empty(B)
    for b in range(B):
        a_perm = a.copy()
        for g in groups:
            if g.size > 1:
                a_perm[g] = a[rng.permutation(g)]
        null[b] = weighted_gap(d, a_perm, groups)
    p = (1 + int(np.count_nonzero(np.abs(null) >= abs(T) - 1e-12))) / (B + 1)

    brng = np.random.default_rng(np.random.SeedSequence(entropy=PERM_SEED, spawn_key=(12, 1)))
    boots = np.empty(BOOT)
    for i in range(BOOT):
        idx = np.concatenate([g[brng.integers(0, g.size, g.size)] for g in groups])
        zb = z_codes[idx]
        gb = [np.flatnonzero(zb == c) for c in np.unique(zb)]
        boots[i] = weighted_gap(d[idx], a[idx], gb)
    lo, hi = np.percentile(boots, [2.5, 97.5])

    trans = np.zeros((6, 6), dtype=int)
    for sp, si in zip(df.s_plain, df.s_ign):
        trans[sp - 1, si - 1] += 1
    trans_by = {}
    for e in (0, 1):
        m = np.zeros((6, 6), dtype=int)
        sub = df[df.ell == e]
        for sp, si in zip(sub.s_plain, sub.s_ign):
            m[sp - 1, si - 1] += 1
        trans_by[f"ELL={e}"] = m.tolist()

    report = {
        "label": "POST-HOC paired analysis; frozen plan section 5.3; NEW post-hoc test, "
                 "outside the Holm family; no equivalence claim from p alone",
        "paired_N": int(len(df)), "paired_ELL_N": int(a.sum()),
        "Delta_plain_paired_sample": round(delta_plain, 4),
        "Delta_ignore_paired_sample": round(delta_ign, 4),
        "attenuation_Delta_ignore_minus_Delta_plain": round(T, 4),
        "permutation_p_two_sided": round(p, 4),
        "bootstrap_95pct_interval": [round(lo, 4), round(hi, 4)],
        "bootstrap_reps": BOOT, "B": B,
        "mean_D_overall": round(float(d.mean()), 4),
        "mean_D_by_ELL": {"ELL=0": round(float(d[a == 0].mean()), 4),
                          "ELL=1": round(float(d[a == 1].mean()), 4)},
        "transition_matrix_rows_plain_cols_ignore_1to6": trans.tolist(),
        "transition_matrix_by_ELL": trans_by,
        "fraction_score_unchanged": round(float((df.d == 0).mean()), 4),
    }
    (OUT / "paired_plain_vs_ignore.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items()
                      if "transition" not in k}, indent=2))


if __name__ == "__main__":
    main()
