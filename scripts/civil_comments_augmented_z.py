#!/usr/bin/env python
"""Civil Comments augmented-Z robustness + common-support decomposition.

Frozen pre-analysis spec: docs/civil_comments_augmented_z_spec.md /
config/civil_comments_augmented_z_spec.json.

Augmented-Z adds a binary comment-length stratum L (L=1 iff character length >
M=225, the A-blind median over the 69,573 manifest) to the exact seven-label
human-annotation vector. For each of the 24 evaluator x identity cells, on the
evaluator's already-frozen valid subset, it runs the frozen ConditionalG2
within-exact-Z_aug permutation test (B=999, slots 20/21/22, Holm across all 24)
and computes the DESCRIPTIVE common-support decomposition of the gap change:

  composition_change  = primary_common_support_gap - primary_gap
  conditioning_change = augmented_gap - primary_common_support_gap
  total_change        = augmented_gap - primary_gap
  (verified: total_change == composition_change + conditioning_change)

No p-values / CIs / multiplicity are attached to the decomposition; it is
descriptive only. The inferential result is the ConditionalG2 Holm family.

Run: .venv/bin/python scripts/civil_comments_augmented_z.py
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
    MANIFEST, MANIFEST_SHA256, B, ALPHA, support, verify, weighted_mean_gap,
)
from civil_comments_freeze import (  # noqa: E402
    BASE_ENTROPY, IDENTITIES, attribute_value, read_rows, sha256_file,
    z_key_exact,
)
from civil_comments_llm_analysis import load_llm_scores, one_test  # noqa: E402
from offcriterion.data import Strata  # noqa: E402

RESULTS = REPO / "results" / "civil_comments"
PROVIDERS = ("gpt", "claude", "gemini")
SLOTS = {"gpt": 20, "claude": 21, "gemini": 22}
M_FROZEN = 225
TOL = 1e-9


def length_bin(row: dict, m: int) -> int:
    return 1 if len(row["comment_text"]) > m else 0


def z_key_augmented(row: dict, m: int) -> str:
    return z_key_exact(row) + "|L=" + str(length_bin(row, m))


def _codes(keys):
    code: dict[str, int] = {}
    return np.array([code.setdefault(k, len(code)) for k in keys], dtype=np.int64)


def holm(cells: dict[str, dict]) -> None:
    ps = {k: v["p_raw"] for k, v in cells.items()}
    order = sorted(ps, key=lambda k: ps[k])
    m = len(order)
    running = 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * ps[k]))
        cells[k]["p_holm"] = running
        cells[k]["reject_holm_at_0.05"] = running <= ALPHA


def decomposition(rows, scores, a_values, m):
    """Descriptive common-support decomposition for one cell.

    Returns augmented_gap, primary_common_support_gap, primary_gap_recomputed,
    and the augmented common-support row count. All gaps use weighted_mean_gap
    over informative (mixed-A) strata under the stated Z coding."""
    keep = np.array([r["id"] in scores for r in rows]) & (a_values >= 0)
    a = a_values[keep].astype(np.int64)
    s = np.array([scores[r["id"]] for r, k in zip(rows, keep) if k], dtype=np.float64)
    kept_rows = [r for r, k in zip(rows, keep) if k]
    z_aug = _codes([z_key_augmented(r, m) for r in kept_rows])
    z_prim = _codes([z_key_exact(r) for r in kept_rows])

    # augmented gap on all kept rows (weighted_mean_gap restricts to informative
    # augmented strata == the common support).
    augmented_gap = weighted_mean_gap(s, a, z_aug)

    # common-support mask: rows in informative (size>=2, mixed-A) augmented strata.
    cs_mask = np.zeros(s.size, dtype=bool)
    for group in Strata.from_codes(z_aug).groups:
        a_g = a[group]
        if group.size >= 2 and a_g.min() != a_g.max():
            cs_mask[group] = True

    if cs_mask.sum() == 0:
        return None, None, weighted_mean_gap(s, a, z_prim), 0

    s_cs, a_cs = s[cs_mask], a[cs_mask]
    prim_keys_cs = [z_key_exact(r) for r, m2 in zip(kept_rows, cs_mask) if m2]
    primary_cs_gap = weighted_mean_gap(s_cs, a_cs, _codes(prim_keys_cs))

    # primary gap recomputed on all kept rows with primary-Z (sanity vs frozen).
    primary_gap_recomp = weighted_mean_gap(s, a, z_prim)
    return augmented_gap, primary_cs_gap, primary_gap_recomp, int(cs_mask.sum())


def main() -> None:
    verify(MANIFEST, MANIFEST_SHA256, "primary manifest")
    rows_all = read_rows()
    by_id = {r["id"]: r for r in rows_all}
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_ids = [r["comment_id"] for r in csv.DictReader(f)]
    primary = sorted((by_id[i] for i in manifest_ids), key=lambda r: int(r["id"]))

    # Assert the frozen A-blind length threshold.
    m = int(np.median([len(r["comment_text"]) for r in primary]))
    if m != M_FROZEN:
        raise SystemExit(f"STOP: median length {m} != frozen M={M_FROZEN}")

    z_aug_keys = [z_key_augmented(r, m) for r in primary]

    scores = {}
    for p in PROVIDERS:
        scores[p], _ = load_llm_scores(p)
        print(f"{p}: {len(scores[p])} valid scores", flush=True)

    frozen_primary = json.loads((RESULTS / "llm_audit_results.json").read_text())
    frozen_cells = frozen_primary["llm_secondary_replication_family"]["tests"]

    def real_a(identity):
        return np.array([attribute_value(r, identity) for r in primary], dtype=np.int64)

    cells: dict[str, dict] = {}
    identity_checks_ok = True
    for p in PROVIDERS:
        slot = SLOTS[p]
        for idx, identity in enumerate(IDENTITIES):
            a_vals = real_a(identity)
            # inferential augmented-Z ConditionalG2 cell (frozen machinery)
            cell = one_test(primary, z_aug_keys, scores[p], slot, identity, idx, a_vals)
            # descriptive decomposition
            aug_gap, prim_cs_gap, prim_gap_recomp, n_cs = decomposition(
                primary, scores[p], a_vals, m
            )
            primary_gap = frozen_cells[f"{p}:{identity}"]["weighted_mean_gap_1to5"]
            # sanity: primary gap recomputed on kept rows equals the frozen value
            if prim_gap_recomp is None or abs(prim_gap_recomp - primary_gap) > 1e-6:
                raise SystemExit(
                    f"STOP: {p}:{identity} recomputed primary gap {prim_gap_recomp} "
                    f"!= frozen {primary_gap}")
            dec = {
                "primary_gap": primary_gap,
                "primary_common_support_gap": prim_cs_gap,
                "augmented_gap": aug_gap,
                "augmented_common_support_n": n_cs,
            }
            if aug_gap is None or prim_cs_gap is None:
                dec.update({
                    "composition_change": None, "conditioning_change": None,
                    "total_change": None, "composition_abs_change": None,
                    "conditioning_abs_change": None, "relative_change": None,
                    "empty_common_support": True, "additive_identity_ok": None,
                })
            else:
                comp = prim_cs_gap - primary_gap
                cond = aug_gap - prim_cs_gap
                tot = aug_gap - primary_gap
                ok = abs(tot - (comp + cond)) <= TOL
                identity_checks_ok = identity_checks_ok and ok
                dec.update({
                    "composition_change": comp,
                    "conditioning_change": cond,
                    "total_change": tot,
                    "composition_abs_change": abs(comp),
                    "conditioning_abs_change": abs(cond),
                    "relative_change": (tot / primary_gap) if primary_gap != 0 else None,
                    "empty_common_support": False,
                    "additive_identity_ok": bool(ok),
                })
            cell.update(dec)
            cell["evaluator"] = p
            cells[f"{p}:{identity}"] = cell
            print(f"  {p}/{identity}: G2={cell['observed_conditional_g2']:.2f} "
                  f"p={cell['p_raw']:.3f} tot={dec.get('total_change')} "
                  f"comp={dec.get('composition_change')} cond={dec.get('conditioning_change')}",
                  flush=True)

    holm(cells)

    # ---- summary ----
    valid = {k: c for k, c in cells.items() if not c["empty_common_support"]}
    big = {k: c for k, c in cells.items()
           if abs(c["primary_gap"]) >= 0.05 and c["relative_change"] is not None}
    med_abs_rel = (float(np.median([abs(c["relative_change"]) for c in big.values()]))
                   if big else None)
    med_abs_comp = float(np.median([c["composition_abs_change"] for c in valid.values()]))
    med_abs_cond = float(np.median([c["conditioning_abs_change"] for c in valid.values()]))
    largest_comp = max(valid, key=lambda k: valid[k]["composition_abs_change"])
    largest_cond = max(valid, key=lambda k: valid[k]["conditioning_abs_change"])
    largest_tot = max(valid, key=lambda k: abs(valid[k]["total_change"]))

    results = {
        "study": "civil_comments_augmented_z_robustness",
        "status": "secondary robustness; descriptive decomposition is descriptive-only",
        "spec": "config/civil_comments_augmented_z_spec.json",
        "frozen_inputs": {
            "primary_manifest_sha256": MANIFEST_SHA256,
            "length_threshold_M": m,
            "score_stores": {
                p: json.loads((RESULTS / f"llm_scores_{p}_FROZEN.json").read_text())
                ["score_store_sha256"] for p in PROVIDERS},
        },
        "n_permutations": B,
        "augmented_z_family": {
            "definition": "3 evaluators x 8 identities; within-exact-(Z,L) permutation; Holm across all 24",
            "tests": cells,
        },
        "prediction_evaluation": {
            "prediction": "median absolute relative change in gap < 15% among cells with primary |gap|>=0.05",
            "n_cells_primary_abs_gap_ge_0.05": len(big),
            "median_abs_relative_change_pct": (med_abs_rel * 100 if med_abs_rel is not None else None),
            "threshold_pct": 15.0,
            "prediction_supported": (med_abs_rel is not None and med_abs_rel < 0.15),
        },
        "decomposition_summary": {
            "median_abs_composition_change": med_abs_comp,
            "median_abs_conditioning_change": med_abs_cond,
            "cell_largest_abs_composition_change": {
                "cell": largest_comp,
                "composition_abs_change": valid[largest_comp]["composition_abs_change"]},
            "cell_largest_abs_conditioning_change": {
                "cell": largest_cond,
                "conditioning_abs_change": valid[largest_cond]["conditioning_abs_change"]},
            "cell_largest_abs_total_change": {
                "cell": largest_tot,
                "primary_gap": valid[largest_tot]["primary_gap"],
                "primary_common_support_gap": valid[largest_tot]["primary_common_support_gap"],
                "augmented_gap": valid[largest_tot]["augmented_gap"],
                "composition_change": valid[largest_tot]["composition_change"],
                "conditioning_change": valid[largest_tot]["conditioning_change"],
                "total_change": valid[largest_tot]["total_change"]},
            "additive_identity_verified_all_24": bool(identity_checks_ok),
            "n_cells_empty_common_support": sum(
                1 for c in cells.values() if c["empty_common_support"]),
        },
    }
    out = RESULTS / "augmented_z_results.json"
    out.write_text(json.dumps(results, indent=2) + "\n")
    n_rej = sum(1 for c in cells.values() if c["reject_holm_at_0.05"])
    rel_str = f"{med_abs_rel*100:.2f}%" if med_abs_rel is not None else "n/a"
    print(f"augmented-Z Holm rejections: {n_rej}/24; additive identity all 24: "
          f"{identity_checks_ok}; median |rel change| (primary|gap|>=.05): {rel_str}")
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
