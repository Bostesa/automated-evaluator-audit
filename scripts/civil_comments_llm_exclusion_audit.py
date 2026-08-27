#!/usr/bin/env python
"""Civil Comments LLM extension -- technical-exclusion/missingness audit.

Runs ONLY after all three LLM score stores are frozen (verify_frozen).
Per the frozen addendum (section technical_exclusion_audit): joins
per-comment technical/invalid STATUS (never scores) to the eight frozen
identity attributes A and simple covariates, and reports:

* overall exclusion rate per provider;
* exclusion counts by identity and two-sided Fisher exact tests;
* comment length as a predictor (excluded vs retained, rank test);
* request-ordering pattern of exclusions;
* Gemini credential/project segments (infrastructure provenance).

This audits missingness; it never modifies the frozen exclusion rules.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact, mannwhitneyu

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from civil_comments_freeze import IDENTITIES, attribute_value, read_rows  # noqa: E402
from offcriterion.pipeline.storage import RawScoreStore  # noqa: E402

RESULTS = REPO / "results" / "civil_comments"
CONFIG = json.loads(
    (REPO / "config" / "civil_comments_llm_evaluator_addendum.json").read_text()
)
PROVIDERS = ("gpt", "claude", "gemini")


def load_status(provider: str) -> dict[str, dict]:
    model = CONFIG["evaluators"][provider]["model_id"]
    root = REPO / "data" / "scoring" / f"cc_{provider}_toxicity"
    RawScoreStore(root).verify_frozen()
    out: dict[str, dict] = {}
    for line in (root / f"scores__{model}__cc_toxicity.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        out[r["essay_id_comp"]] = {
            "excluded": bool(r.get("error_status")) or r.get("parsed_score") is None,
            "technical": bool(r.get("error_status")),
            "invalid": (not r.get("error_status")) and r.get("parsed_score") is None,
            "retry_count": int(r.get("retry_count", 0)),
            "error_status": (r.get("error_status") or "")[:40],
        }
    return out


def main() -> None:
    rows = read_rows()
    by_id = {r["id"]: r for r in rows}
    with (RESULTS / "primary_manifest.csv").open(newline="", encoding="utf-8") as f:
        ids = sorted((r["comment_id"] for r in csv.DictReader(f)), key=int)
    manifest_rows = [by_id[i] for i in ids]
    a_mat = {
        ident: np.array([attribute_value(r, ident) for r in manifest_rows], dtype=np.int64)
        for ident in IDENTITIES
    }
    lengths = np.array([len(r["comment_text"]) for r in manifest_rows])

    audit: dict[str, object] = {"n_manifest": len(ids)}
    for p in PROVIDERS:
        st = load_status(p)
        exc = np.array([st[i]["excluded"] for i in ids], dtype=bool)
        tech = sum(st[i]["technical"] for i in ids)
        inv = sum(st[i]["invalid"] for i in ids)
        rep: dict[str, object] = {
            "n_records": len(st),
            "n_excluded": int(exc.sum()),
            "n_technical": tech,
            "n_invalid_response": inv,
            "exclusion_rate": float(exc.mean()),
            "total_retries": int(sum(st[i]["retry_count"] for i in ids)),
            "error_status_kinds": sorted({st[i]["error_status"] for i in ids if st[i]["technical"]}),
        }
        by_identity = {}
        for ident in IDENTITIES:
            a = a_mat[ident]
            t = [[int((exc & (a == 1)).sum()), int((~exc & (a == 1)).sum())],
                 [int((exc & (a == 0)).sum()), int((~exc & (a == 0)).sum())]]
            if exc.sum() == 0:
                p_f = 1.0
            else:
                p_f = float(fisher_exact(t, alternative="two-sided")[1])
            by_identity[ident] = {
                "excluded_a1": t[0][0], "retained_a1": t[0][1],
                "excluded_a0": t[1][0], "retained_a0": t[1][1],
                "fisher_two_sided_p": p_f,
            }
        rep["by_identity"] = by_identity
        if exc.sum() > 0:
            rep["comment_length"] = {
                "median_excluded": float(np.median(lengths[exc])),
                "median_retained": float(np.median(lengths[~exc])),
                "mannwhitney_two_sided_p": float(
                    mannwhitneyu(lengths[exc], lengths[~exc], alternative="two-sided")[1]
                ),
            }
            pos = np.nonzero(exc)[0]
            rep["request_order_positions_of_exclusions"] = {
                "first_decile_count": int((pos < len(ids) // 10).sum()),
                "last_decile_count": int((pos >= len(ids) - len(ids) // 10).sum()),
                "positions_summary": [int(pos.min()), int(np.median(pos)), int(pos.max())],
            }
        else:
            rep["comment_length"] = "no exclusions"
        audit[p] = rep

    prov = RESULTS / "gemini_credential_provenance.json"
    if prov.exists():
        audit["gemini_credential_segments"] = json.loads(prov.read_text())["segments"]

    out = RESULTS / "llm_exclusion_audit.json"
    out.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({p: {k: audit[p][k] for k in ("n_excluded", "n_technical", "n_invalid_response", "exclusion_rate")} for p in PROVIDERS}, indent=2))
    print("written:", out.relative_to(REPO))


if __name__ == "__main__":
    main()
