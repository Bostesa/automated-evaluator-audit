#!/usr/bin/env python
"""Civil Comments additional audit -- Stages 3-4: verify and freeze scores.

Stage 3 (A-blind verification of the raw score store):

* one row per expected comment id, no duplicates, frozen order;
* every successful score finite and in [0, 1];
* technical failure count and truncation count reported;
* SHA-256 of the complete raw score store recorded.

Stage 4 (frozen A-blind decile discretisation, config
``score_discretization``):

* nine requested quantiles k/10 via ``np.quantile(method='linear')``
  over the pooled successful census scores;
* ``np.unique`` collapse of coincident boundaries;
* ``np.searchsorted(side='right')`` category assignment;
* boundary artifact, discrete score store, and SHA-256 of all three
  score artifacts recorded in ``scores_FROZEN.json``.

Only pooled, A-blind quantities are computed or printed here.  No
identity attribute, human label, or article field is read.

Run:  python3 scripts/civil_comments_score_freeze.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from civil_comments_freeze import discretize_scores, sha256_file  # noqa: E402

DATASET_CSV = REPO / "data" / "civil_comments" / "all_data_with_identities.csv"
DATASET_SHA256 = "403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f"

RESULTS = REPO / "results" / "civil_comments"
RAW = RESULTS / "scores_raw.csv"
BOUNDARIES = RESULTS / "score_decile_boundaries.json"
DISCRETE = RESULTS / "scores_discrete.csv"
FROZEN = RESULTS / "scores_FROZEN.json"


def expected_ids() -> list[str]:
    """Comment ids only (A-blind), in the frozen ascending-integer order."""
    if sha256_file(DATASET_CSV) != DATASET_SHA256:
        raise SystemExit("STOP: dataset hash mismatch")
    with DATASET_CSV.open(newline="", encoding="utf-8") as f:
        ids = [row["id"] for row in csv.DictReader(f)]
    ids.sort(key=int)
    return ids


def main() -> None:
    if FROZEN.exists():
        raise SystemExit("STOP: scores_FROZEN.json already exists; refusing to re-freeze")

    ids = expected_ids()

    with RAW.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Stage 3.1-3.2: coverage and uniqueness
    if len(rows) != len(ids):
        raise SystemExit(f"STOP: score store has {len(rows)} rows, expected {len(ids)}")
    got_ids = [r["comment_id"] for r in rows]
    if got_ids != ids:
        raise SystemExit("STOP: score store ids do not match expected frozen ordering")
    if len(set(got_ids)) != len(got_ids):
        raise SystemExit("STOP: duplicate comment ids in score store")

    ok = [r for r in rows if r["status"].startswith("ok")]
    failed = [r for r in rows if not r["status"].startswith("ok")]
    fallbacks = [r for r in rows if r["status"] == "ok_singleton_fallback"]
    scores = np.array([float(r["toxicity"]) for r in ok], dtype=np.float64)

    # Stage 3.3: finite and in [0,1]
    if not np.all(np.isfinite(scores)):
        raise SystemExit("STOP: non-finite score present")
    if scores.min() < 0.0 or scores.max() > 1.0:
        raise SystemExit("STOP: score outside [0,1]")

    n_truncated = sum(1 for r in rows if r["truncated"] == "1")

    raw_sha = sha256_file(RAW)

    # Stage 4: frozen discretisation over pooled successful scores
    requested_q = [k / 10 for k in range(1, 10)]
    raw_quantiles = np.quantile(scores, requested_q, method="linear")
    boundaries, cats = discretize_scores(scores)
    n_categories = int(len(boundaries)) + 1
    pooled_counts = np.bincount(cats, minlength=n_categories).tolist()

    boundary_artifact = {
        "rule": "frozen A-blind pooled decile rule (config score_discretization)",
        "requested_quantiles": requested_q,
        "raw_quantile_values": [repr(float(v)) for v in raw_quantiles],
        "unique_boundaries": [repr(float(b)) for b in boundaries],
        "n_boundaries_after_unique_collapse": int(len(boundaries)),
        "n_categories": n_categories,
        "pooled_category_counts": pooled_counts,
        "n_scores_pooled": int(scores.size),
    }
    BOUNDARIES.write_text(json.dumps(boundary_artifact, indent=2) + "\n")

    # Discrete score store, same order/keying as the raw store
    it = iter(cats.tolist())
    with DISCRETE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "s_category", "status"])
        for r in rows:
            if r["status"].startswith("ok"):
                w.writerow([r["comment_id"], next(it), r["status"]])
            else:
                w.writerow([r["comment_id"], "", r["status"]])

    meta = {
        "stage": "3-4 (verify and freeze raw scores; frozen discretisation)",
        "n_expected": len(ids),
        "n_rows": len(rows),
        "n_ok": len(ok),
        "n_technical_failures": len(failed),
        "technical_failure_ids": [r["comment_id"] for r in failed],
        "n_singleton_fallbacks": len(fallbacks),
        "singleton_fallback_ids": [r["comment_id"] for r in fallbacks],
        "n_truncated_at_512": n_truncated,
        "pooled_score_properties_a_blind": {
            "count": int(scores.size),
            "min": repr(float(scores.min())),
            "max": repr(float(scores.max())),
            "mean": repr(float(scores.mean())),
            "quantiles": {str(q): repr(float(v)) for q, v in zip(requested_q, raw_quantiles)},
            "n_unique_values": int(np.unique(scores).size),
        },
        "discretization": boundary_artifact,
        "artifact_sha256": {
            "scores_raw.csv": raw_sha,
            "score_decile_boundaries.json": sha256_file(BOUNDARIES),
            "scores_discrete.csv": sha256_file(DISCRETE),
        },
    }
    FROZEN.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in (
        "n_rows", "n_ok", "n_technical_failures", "n_singleton_fallbacks",
        "n_truncated_at_512", "pooled_score_properties_a_blind", "artifact_sha256")}, indent=2))
    print("frozen:", FROZEN.relative_to(REPO))


if __name__ == "__main__":
    main()
