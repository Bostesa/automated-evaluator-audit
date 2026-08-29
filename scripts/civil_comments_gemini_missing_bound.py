#!/usr/bin/env python
"""Civil Comments Gemini missing-score worst-case bound (descriptive).

Frozen pre-analysis spec: docs/civil_comments_gemini_missing_bound_spec.md /
config/civil_comments_gemini_missing_bound_spec.json.

For each of the eight identities, on the frozen Gemini store, computes the
observed primary weighted conditional-gap over the 67,183 valid rows and the
worst-case lower/upper bounds obtained by supplying bounded scores in [1,5] to
the 2,390 frozen missing rows:

  lower: missing A=1 -> 1, missing A=0 -> 5
  upper: missing A=1 -> 5, missing A=0 -> 1

Bounds use the intended primary support (informative primary-Z strata) on the
resulting complete data. Descriptive only: no p-values, no multiplicity, no
alteration of any frozen result. Uses frozen data only; no APIs.

Run: .venv/bin/python scripts/civil_comments_gemini_missing_bound.py
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
    MANIFEST, MANIFEST_SHA256, verify, weighted_mean_gap,
)
from civil_comments_freeze import (  # noqa: E402
    IDENTITIES, attribute_value, read_rows, sha256_file, z_key_exact,
)

RESULTS = REPO / "results" / "civil_comments"
GEM_STORE = (REPO / "data" / "scoring" / "cc_gemini_toxicity"
             / "scores__gemini-3.7-flash__cc_toxicity.jsonl")
GEM_STORE_SHA = "3ef469677c9ae7f0a89924af3476fc0b92c352376b464d8b888efa454a4f58f1"


def _codes(keys):
    code: dict[str, int] = {}
    return np.array([code.setdefault(k, len(code)) for k in keys], dtype=np.int64)


def main() -> None:
    verify(MANIFEST, MANIFEST_SHA256, "primary manifest")
    if sha256_file(GEM_STORE) != GEM_STORE_SHA:
        raise SystemExit("STOP: Gemini store hash mismatch")

    rows_all = read_rows()
    by_id = {r["id"]: r for r in rows_all}
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_ids = [r["comment_id"] for r in csv.DictReader(f)]
    primary = sorted((by_id[i] for i in manifest_ids), key=lambda r: int(r["id"]))

    # Frozen Gemini records: valid score dict and the missing-id set.
    valid: dict[str, int] = {}
    missing: set[str] = set()
    for line in GEM_STORE.open(encoding="utf-8"):
        rec = json.loads(line)
        cid = rec["essay_id_comp"]
        if not rec.get("error_status") and rec.get("parsed_score") is not None:
            valid[cid] = int(rec["parsed_score"])
        else:
            missing.add(cid)
    if len(valid) != 67183 or len(missing) != 2390:
        raise SystemExit(f"STOP: unexpected counts valid={len(valid)} missing={len(missing)}")

    frozen_primary = json.loads((RESULTS / "llm_audit_results.json").read_text())
    frozen_cells = frozen_primary["llm_secondary_replication_family"]["tests"]

    ids = [r["id"] for r in primary]
    z_prim = [z_key_exact(r) for r in primary]
    n = len(primary)
    is_missing = np.array([cid in missing for cid in ids])

    rows_out = {}
    for identity in IDENTITIES:
        a = np.array([attribute_value(r, identity) for r in primary], dtype=np.int64)

        # observed gap on valid rows only (must equal frozen primary Gemini gap)
        keep_valid = np.array([cid in valid for cid in ids])
        s_valid = np.array([valid[cid] for cid, k in zip(ids, keep_valid) if k],
                           dtype=np.float64)
        a_valid = a[keep_valid]
        z_valid = _codes([z_prim[j] for j in range(n) if keep_valid[j]])
        observed = weighted_mean_gap(s_valid, a_valid, z_valid)
        frozen_gap = frozen_cells[f"gemini:{identity}"]["weighted_mean_gap_1to5"]
        if observed is None or abs(observed - frozen_gap) > 1e-6:
            raise SystemExit(
                f"STOP: {identity} observed gap {observed} != frozen {frozen_gap}")

        # full-data scores with bounded imputation, primary support on all rows
        base = np.array([valid.get(cid, 0) for cid in ids], dtype=np.float64)
        z_full = _codes(z_prim)

        s_low = base.copy()
        s_low[is_missing & (a == 1)] = 1.0
        s_low[is_missing & (a == 0)] = 5.0
        lower = weighted_mean_gap(s_low, a, z_full)

        s_up = base.copy()
        s_up[is_missing & (a == 1)] = 5.0
        s_up[is_missing & (a == 0)] = 1.0
        upper = weighted_mean_gap(s_up, a, z_full)

        m_a1 = int((is_missing & (a == 1)).sum())
        m_a0 = int((is_missing & (a == 0)).sum())
        zero_in = (lower <= 0.0 <= upper)
        rows_out[identity] = {
            "observed_primary_gemini_gap": observed,
            "total_missing": int(is_missing.sum()),
            "missing_a1": m_a1,
            "missing_a0": m_a0,
            "worst_case_lower_bound_gap": lower,
            "worst_case_upper_bound_gap": upper,
            "interval_width": upper - lower,
            "zero_in_interval": bool(zero_in),
            "positive_sign_guaranteed": bool(lower > 0.0),
        }
        print(f"  {identity:16s} obs={observed:+.4f} low={lower:+.4f} up={upper:+.4f} "
              f"m1={m_a1} m0={m_a0} zero_in={zero_in} sign_guaranteed={lower>0}",
              flush=True)

    widths = {i: rows_out[i]["interval_width"] for i in IDENTITIES}
    narrow = min(widths, key=widths.get)
    wide = max(widths, key=widths.get)
    identified = [i for i in IDENTITIES if not rows_out[i]["zero_in_interval"]]
    not_identified = [i for i in IDENTITIES if rows_out[i]["zero_in_interval"]]

    result = {
        "study": "civil_comments_gemini_missing_score_bound",
        "status": "descriptive missing-outcome sensitivity; no p-values, no multiplicity; frozen results unaltered",
        "spec": "config/civil_comments_gemini_missing_bound_spec.json",
        "frozen_inputs": {
            "manifest_sha256": MANIFEST_SHA256,
            "gemini_store_sha256": GEM_STORE_SHA,
            "gemini_valid": len(valid),
            "gemini_missing_total": len(missing),
        },
        "bounds": rows_out,
        "summary": {
            "narrowest_interval": {"identity": narrow, "width": widths[narrow]},
            "widest_interval": {"identity": wide, "width": widths[wide]},
            "sign_identified": identified,
            "sign_not_identified": not_identified,
        },
    }
    out = RESULTS / "gemini_missing_bound.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"sign identified: {identified}")
    print(f"sign NOT identified: {not_identified}")
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
