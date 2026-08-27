#!/usr/bin/env python
"""Civil Comments LLM-evaluator extension -- frozen 24-test analysis.

Runs, exactly as frozen in ``config/civil_comments_llm_evaluator_addendum.json``:

* the secondary replication family: 3 LLM evaluators x 8 identities on the
  one-comment-per-article sample under exact Z, ConditionalG2, B = 999,
  seeds SeedSequence(entropy=20260827, spawn_key=(slot, identity_index))
  with slots 11/12/13 (gpt/claude/gemini), Holm across ALL 24 raw
  permutation p-values;
* per-evaluator binned-Z sensitivity (slots 14/15/16);
* per-evaluator negative control on the frozen labels (slots 17/18/19).

S is the frozen integer 1-5 rating used directly (5 categories); the
descriptive gap is the stratum-size-weighted conditional mean difference on
the 1-5 scale.  Each evaluator is analyzed on its validly scored subset of
the manifest; technical/invalid exclusions are dropped and counted, never
imputed.  Every input hash is verified; each store must be frozen
(``verify_frozen``) before this script will read it.

Run:  .venv/bin/python scripts/civil_comments_llm_analysis.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from civil_comments_analysis import (  # noqa: E402
    MANIFEST, MANIFEST_SHA256, NC_LABELS, NC_SHA256, B, ALPHA,
    support, verify, weighted_mean_gap,
)
from civil_comments_freeze import (  # noqa: E402
    BASE_ENTROPY, IDENTITIES, attribute_value, read_rows, sha256_file,
    z_key_binned, z_key_exact,
)
from offcriterion.data import Sample, Strata  # noqa: E402
from offcriterion.permutation import permutation_test  # noqa: E402
from offcriterion.pipeline.storage import RawScoreStore  # noqa: E402

RESULTS = REPO / "results" / "civil_comments"
CONFIG = json.loads(
    (REPO / "config" / "civil_comments_llm_evaluator_addendum.json").read_text()
)
N_CATEGORIES = 5
SLOTS = {
    "primary": {"gpt": 11, "claude": 12, "gemini": 13},
    "binned": {"gpt": 14, "claude": 15, "gemini": 16},
    "negative_control": {"gpt": 17, "claude": 18, "gemini": 19},
}
PROVIDERS = ("gpt", "claude", "gemini")


def load_llm_scores(provider: str) -> tuple[dict[str, int], dict]:
    model = CONFIG["evaluators"][provider]["model_id"]
    root = REPO / "data" / "scoring" / f"cc_{provider}_toxicity"
    store = RawScoreStore(root)
    store.verify_frozen()
    frozen_meta = json.loads(
        (RESULTS / f"llm_scores_{provider}_FROZEN.json").read_text()
    )
    path = root / f"scores__{model}__cc_toxicity.jsonl"
    if sha256_file(path) != frozen_meta["score_store_sha256"]:
        raise SystemExit(f"STOP: {provider} score store hash mismatch")
    scores: dict[str, int] = {}
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        if not rec.get("error_status") and rec.get("parsed_score") is not None:
            scores[rec["essay_id_comp"]] = int(rec["parsed_score"])
    return scores, frozen_meta


def one_test(rows, z_keys, scores, slot, identity, idx, a_values):
    """One ConditionalG2 permutation cell on the evaluator's valid subset."""
    keep = np.array([r["id"] in scores for r in rows]) & (a_values >= 0)
    a = a_values[keep].astype(np.int64)
    s = np.array([scores[r["id"]] for r, k in zip(rows, keep) if k], dtype=np.int64)
    sub_keys = [z_keys[j] for j in range(len(z_keys)) if keep[j]]
    code: dict[str, int] = {}
    z = np.array([code.setdefault(k, len(code)) for k in sub_keys], dtype=np.int64)
    s_raw = s.astype(np.float64)
    sample = Sample(
        s_raw=s_raw, s_bin=s - 1, a=a, z=z,
        n_s_bins=N_CATEGORIES, n_a=2, n_z=int(z.max()) + 1,
    )
    rng = np.random.default_rng(
        np.random.SeedSequence(entropy=BASE_ENTROPY, spawn_key=(slot, idx))
    )
    res = permutation_test(sample, ("conditional_g2",), B, rng)["conditional_g2"]
    return {
        "identity_index": idx,
        "seed_spawn_key": [slot, idx],
        **support(a, z),
        "observed_conditional_g2": res.observed,
        "n_permutations": res.n_permutations,
        "permutation_exceedance_count": res.n_at_least_observed,
        "p_raw": res.p_value,
        "weighted_mean_gap_1to5": weighted_mean_gap(s_raw, a, z),
    }


def holm(cells: dict[str, dict]) -> None:
    ps = {k: v["p_raw"] for k, v in cells.items()}
    order = sorted(ps, key=lambda k: ps[k])
    m = len(order)
    running = 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * ps[k]))
        cells[k]["p_holm"] = running
        cells[k]["reject_holm_at_0.05"] = running <= ALPHA


def main() -> None:
    verify(MANIFEST, MANIFEST_SHA256, "primary manifest")
    verify(NC_LABELS, NC_SHA256, "negative-control labels")
    rows = read_rows()
    by_id = {r["id"]: r for r in rows}
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_ids = [r["comment_id"] for r in csv.DictReader(f)]
    primary = sorted((by_id[i] for i in manifest_ids), key=lambda r: int(r["id"]))
    z_exact = [z_key_exact(r) for r in primary]
    z_binned = [z_key_binned(r) for r in primary]
    with NC_LABELS.open(newline="", encoding="utf-8") as f:
        nc_rows = {r["comment_id"]: r for r in csv.DictReader(f)}

    def real_a(identity):
        return np.array([attribute_value(r, identity) for r in primary], dtype=np.int64)

    def nc_a(identity):
        return np.array(
            [int(nc_rows[r["id"]][f"nc_{identity}"]) for r in primary], dtype=np.int64
        )

    scores: dict[str, dict[str, int]] = {}
    metas: dict[str, dict] = {}
    for p in PROVIDERS:
        scores[p], metas[p] = load_llm_scores(p)
        print(f"{p}: {len(scores[p])} valid scores", flush=True)

    results: dict[str, object] = {
        "study": "civil_comments_llm_evaluator_extension",
        "frozen_inputs": {
            "addendum_config": "config/civil_comments_llm_evaluator_addendum.json",
            "primary_manifest_sha256": MANIFEST_SHA256,
            "negative_control_labels_sha256": NC_SHA256,
            "score_stores": {p: metas[p]["score_store_sha256"] for p in PROVIDERS},
            "model_ids": {p: CONFIG["evaluators"][p]["model_id"] for p in PROVIDERS},
        },
        "n_permutations": B,
    }

    # Secondary replication family: Holm across ALL 24 cells.
    family: dict[str, dict] = {}
    for p in PROVIDERS:
        slot = SLOTS["primary"][p]
        for idx, identity in enumerate(IDENTITIES):
            cell = one_test(primary, z_exact, scores[p], slot, identity, idx, real_a(identity))
            cell["evaluator"] = CONFIG["evaluators"][p]["model_id"]
            family[f"{p}:{identity}"] = cell
            print(f"  primary {p}/{identity}: G2={cell['observed_conditional_g2']:.3f} "
                  f"p={cell['p_raw']:.3f}", flush=True)
    holm(family)
    results["llm_secondary_replication_family"] = {
        "definition": "3 evaluators x 8 identities; Holm across all 24 raw p-values",
        "status": "secondary cross-evaluator replication; NOT the original confirmatory family",
        "tests": family,
    }

    for kind, z_keys, a_fn in (
        ("binned", z_binned, real_a),
        ("negative_control", z_exact, nc_a),
    ):
        block: dict[str, dict] = {}
        for p in PROVIDERS:
            slot = SLOTS[kind][p]
            cells: dict[str, dict] = {}
            for idx, identity in enumerate(IDENTITIES):
                cell = one_test(primary, z_keys, scores[p], slot, identity, idx, a_fn(identity))
                cells[identity] = cell
                print(f"  {kind} {p}/{identity}: p={cell['p_raw']:.3f}", flush=True)
            block[p] = {"analysis_slot": slot, "tests": cells}
        key = "sensitivity_binned_z" if kind == "binned" else "negative_control"
        results[key] = block
    results["negative_control"]["status"] = "calibration sanity check, NOT confirmatory"

    out = RESULTS / "llm_audit_results.json"
    out.write_text(json.dumps(results, indent=2) + "\n")
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
