"""POST-HOC Stage 2/4 feasibility: Z1 and Z2 strata on the manifest + ELL.

Frozen plan sections 2.2, 2.3, 4.  Joins ELL status but NO judge scores.
Also writes the frozen per-essay bin assignments used by the later tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "posthoc"


def tertile_bin(values: pd.Series) -> pd.Series:
    q1, q2 = np.quantile(values, [1 / 3, 2 / 3])
    return pd.Series(np.where(values <= q1, 0, np.where(values <= q2, 1, 2)),
                     index=values.index)


def median_bin(values: pd.Series) -> pd.Series:
    med = np.median(values)
    return pd.Series(np.where(values <= med, 0, 1), index=values.index)


def feasibility(df: pd.DataFrame, cols: list[str]) -> dict:
    g = df.groupby(cols, observed=True)
    sizes = g.size()
    both = g.ell.agg(lambda x: x.min() != x.max())
    informative = (sizes >= 2) & both
    inf_idx = informative[informative].index
    keep = df.set_index(cols).index.isin(inf_idx)
    kept = df[keep]
    return {
        "total_strata": int(len(sizes)),
        "informative_strata": int(informative.sum()),
        "degenerate_strata_size1": int((sizes == 1).sum()),
        "thin_strata_size_lt10": int((sizes < 10).sum()),
        "effective_N": int(len(kept)),
        "ELL_N": int(kept.ell.sum()),
        "fraction_ELL_retained": round(float(kept.ell.sum()) / 1039, 4),
        "fraction_N_retained": round(len(kept) / 11360, 4),
        "stratum_size_min": int(sizes.min()),
        "stratum_size_median": float(sizes.median()),
        "stratum_size_max": int(sizes.max()),
        "gate_70pct_ELL": bool(kept.ell.sum() >= 0.70 * 1039),
        "gate_20_informative": bool(informative.sum() >= 20),
        "PASS": bool(kept.ell.sum() >= 0.70 * 1039 and informative.sum() >= 20),
    }


def main() -> None:
    man = pd.read_csv(ROOT / "data/scoring/primary_sample_manifest.csv")
    q = pd.read_csv(OUT / "quality_index.csv")
    frozen = json.loads((OUT / "quality_index_FROZEN.json").read_text())
    actual = hashlib.sha256((OUT / "quality_index.csv").read_bytes()).hexdigest()
    assert actual == frozen["sha256"], "quality index changed after freeze"

    lvl = pd.read_csv(ROOT / "data/persuade/persuade_essay_level.csv",
                      usecols=["essay_id_comp", "holistic_essay_score", "ell_status",
                               "essay_word_count"])
    df = man.merge(q, on="essay_id_comp").merge(lvl, on="essay_id_comp")
    assert len(df) == 11360
    df["ell"] = (df.ell_status == "Yes").astype(int)
    assert df.ell.sum() == 1039

    z0 = ["prompt_name", "holistic_essay_score"]
    df["qbin"] = df.groupby(z0, observed=True, group_keys=False).quality_index.apply(tertile_bin)
    z1 = z0 + ["qbin"]
    df["lbin"] = df.groupby(z1, observed=True, group_keys=False).essay_word_count.apply(median_bin)
    z2 = z1 + ["lbin"]

    report = {
        "label": "POST-HOC feasibility; frozen plan section 4; manifest + ELL only, no judge scores",
        "Z0": feasibility(df, z0),
        "Z1": feasibility(df, z1),
        "Z2": feasibility(df, z2),
    }
    (OUT / "feasibility.json").write_text(json.dumps(report, indent=2))

    bins = df[["essay_id_comp", "qbin", "lbin"]].sort_values("essay_id_comp")
    bins_csv = OUT / "strata_bins.csv"
    bins.to_csv(bins_csv, index=False)
    (OUT / "strata_bins_FROZEN.json").write_text(json.dumps({
        "file": bins_csv.name,
        "sha256": hashlib.sha256(bins_csv.read_bytes()).hexdigest(),
        "rule": "qbin: within-(prompt,Y) tertile value-cut of quality_index; "
                "lbin: within-(prompt,Y,qbin) median value-cut of essay_word_count",
    }, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
