#!/usr/bin/env python
"""Civil Comments -- descriptive cross-evaluator summary.

Runs ONLY after both frozen result artifacts exist:
  results/civil_comments/audit_results.json       (Detoxify, commit 44efcd1)
  results/civil_comments/llm_audit_results.json   (GPT/Claude/Gemini)

Purely descriptive: no new test is computed.  For each of the eight frozen
identities it tabulates, for all four evaluators, the conditional gap, raw
permutation p, and the Holm-adjusted p from each evaluator's own
prespecified family (Detoxify: 8-test family; LLMs: 24-test family), plus
direction-agreement summaries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from civil_comments_freeze import IDENTITIES  # noqa: E402

RESULTS = REPO / "results" / "civil_comments"
PROVIDERS = ("gpt", "claude", "gemini")


def main() -> None:
    detox = json.loads((RESULTS / "audit_results.json").read_text())
    llm = json.loads((RESULTS / "llm_audit_results.json").read_text())
    fam = llm["llm_secondary_replication_family"]["tests"]

    table: dict[str, dict] = {}
    for ident in IDENTITIES:
        d = detox["primary_family"]["tests"][ident]
        row = {
            "detoxify": {
                "gap": d["weighted_mean_gap_raw_probability"],
                "gap_scale": "raw toxicity probability",
                "p_raw": d["p_raw"],
                "p_holm_8test_family": d["p_holm"],
                "reject_holm": d["reject_holm_at_0.05"],
            }
        }
        for p in PROVIDERS:
            c = fam[f"{p}:{ident}"]
            row[p] = {
                "gap": c["weighted_mean_gap_1to5"],
                "gap_scale": "1-5 integer score",
                "p_raw": c["p_raw"],
                "p_holm_24test_family": c["p_holm"],
                "reject_holm": c["reject_holm_at_0.05"],
            }
        gaps = [row["detoxify"]["gap"]] + [row[p]["gap"] for p in PROVIDERS]
        row["gap_directions"] = ["+" if g > 0 else "-" if g < 0 else "0" for g in gaps]
        row["same_direction_all_four"] = len({d for d in row["gap_directions"]}) == 1
        table[ident] = row

    n_detox = sum(table[i]["detoxify"]["reject_holm"] for i in IDENTITIES)
    n_llm = sum(fam[k]["reject_holm_at_0.05"] for k in fam)
    summary = {
        "study": "civil_comments_cross_evaluator_summary (descriptive; no new test)",
        "identities": table,
        "n_detoxify_holm_rejections_of_8": n_detox,
        "n_llm_holm_rejections_of_24": n_llm,
        "identities_same_gap_direction_all_four": [
            i for i in IDENTITIES if table[i]["same_direction_all_four"]],
        "frozen_inputs": {
            "detoxify_results": "audit_results.json (frozen, commit 44efcd1)",
            "llm_results": "llm_audit_results.json",
        },
    }
    out = RESULTS / "cross_evaluator_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("detoxify Holm rejections:", n_detox, "/8; LLM Holm rejections:", n_llm, "/24")
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
