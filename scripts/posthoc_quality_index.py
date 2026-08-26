"""POST-HOC Stage 1: essay-level human quality index Q.

Frozen plan: docs/posthoc_robustness_plan.md section 2.1.  Reads ONLY the
frozen manifest, the canonical corpus discourse rows, and (for the Q-vs-Y
descriptive) the human holistic score.  No ELL status, no judge output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "posthoc"
MAP = {"Ineffective": 0, "Adequate": 1, "Effective": 2}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    man = pd.read_csv(ROOT / "data/scoring/primary_sample_manifest.csv")
    manifest_ids = set(man.essay_id_comp)
    assert len(manifest_ids) == 11360

    cols = ["essay_id_comp", "discourse_start", "discourse_end", "discourse_type", "discourse_effectiveness"]
    rows = pd.concat(
        [
            pd.read_csv(ROOT / "data/persuade/persuade_train.csv", usecols=cols),
            pd.read_csv(ROOT / "data/persuade/persuade_corpus_2.0_test.csv", usecols=cols),
        ],
        ignore_index=True,
    )
    rows = rows[rows.essay_id_comp.isin(manifest_ids)]
    n_before = len(rows)
    rows = rows.drop_duplicates(subset=["essay_id_comp", "discourse_start", "discourse_end"])
    n_dupes = n_before - len(rows)

    ann = rows.dropna(subset=["discourse_effectiveness"]).copy()
    unexpected = set(ann.discourse_effectiveness) - set(MAP)
    if unexpected:
        raise SystemExit(f"unexpected effectiveness labels: {unexpected}")
    ann["eff"] = ann.discourse_effectiveness.map(MAP)

    q = (
        ann.groupby("essay_id_comp")["eff"]
        .agg(n_effectiveness_elements="size", quality_index="mean")
        .reset_index()
        .sort_values("essay_id_comp")
    )
    q["quality_index"] = q.quality_index.round(6)
    missing = manifest_ids - set(q.essay_id_comp)

    out_csv = OUT / "quality_index.csv"
    q.to_csv(out_csv, index=False)
    digest = sha256(out_csv)
    (OUT / "quality_index_FROZEN.json").write_text(
        json.dumps({"file": out_csv.name, "sha256": digest,
                    "note": "frozen BEFORE any join with ELL status or judge scores"}, indent=2)
    )

    # Descriptives (A-free, S-free; Y is the human holistic score).
    lvl = pd.read_csv(ROOT / "data/persuade/persuade_essay_level.csv",
                      usecols=["essay_id_comp", "holistic_essay_score"])
    m = q.merge(lvl, on="essay_id_comp", how="left")
    per = q.n_effectiveness_elements
    qi = q.quality_index
    desc = {
        "label": "POST-HOC descriptive; frozen plan section 2.1",
        "duplicate_discourse_rows_dropped": int(n_dupes),
        "n_manifest": 11360,
        "n_with_usable_annotations": int(len(q)),
        "fraction_usable": round(len(q) / 11360, 4),
        "n_missing_quality_index": int(len(missing)),
        "elements_per_essay": {
            "min": int(per.min()), "p25": float(per.quantile(0.25)),
            "median": float(per.median()), "p75": float(per.quantile(0.75)),
            "max": int(per.max()), "mean": round(float(per.mean()), 2),
        },
        "quality_index_distribution": {
            "min": float(qi.min()), "p10": round(float(qi.quantile(0.10)), 4),
            "p25": round(float(qi.quantile(0.25)), 4),
            "median": round(float(qi.median()), 4),
            "p75": round(float(qi.quantile(0.75)), 4),
            "p90": round(float(qi.quantile(0.90)), 4),
            "max": float(qi.max()), "mean": round(float(qi.mean()), 4),
            "sd": round(float(qi.std()), 4),
            "n_distinct_values": int(qi.nunique()),
        },
        "element_effectiveness_marginal": ann.discourse_effectiveness.value_counts().to_dict(),
        "relationship_with_holistic_score": {
            "spearman_rho": round(float(m.quality_index.corr(m.holistic_essay_score, method="spearman")), 4),
            "pearson_r": round(float(m.quality_index.corr(m.holistic_essay_score)), 4),
            "mean_Q_by_Y": {int(k): round(float(v), 4)
                            for k, v in m.groupby("holistic_essay_score").quality_index.mean().items()},
            "sd_Q_within_Y_mean": round(float(m.groupby("holistic_essay_score").quality_index.std().mean()), 4),
        },
        "sha256_quality_index_csv": digest,
    }
    (OUT / "quality_index_descriptives.json").write_text(json.dumps(desc, indent=2))
    print(json.dumps(desc, indent=2))


if __name__ == "__main__":
    main()
