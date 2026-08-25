"""PERSUADE 2.0 feasibility analysis for the OffCriterion real-data design.

Proposed primary null (observational, not causal):

    H0 :  S  _||_  A  |  Y, P

with S = LLM judge holistic score (not yet collected), A = writer ELL status,
Y = human holistic score (1-6), P = writing prompt.  This script audits the
conditioning structure (P x Y strata and within-stratum ELL variation) that the
stratified permutation test would use.  No pooling of sparse strata is applied;
sparsity is reported, not repaired.

Input : data/persuade/persuade_essay_level.csv  (one row per unique essay,
        deduplicated from the canonical discourse-level train+test CSVs)
Output: results/persuade_feasibility/strata.csv        full (P, Y) stratum table
        results/persuade_feasibility/cells.csv         full (P, Y, ELL) cell table
        results/persuade_feasibility/feasibility.json  headline statistics
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "persuade" / "persuade_essay_level.csv"
OUT = ROOT / "results" / "persuade_feasibility"


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    rows = list(csv.DictReader(DATA.open(newline="", encoding="utf-8")))
    n_total = len(rows)

    # --- identifiers and duplicates -------------------------------------
    id_comp = Counter(r["essay_id_comp"] for r in rows)
    id_raw = Counter(r["essay_id"] for r in rows)
    text_hash = Counter(r["text_sha1"] for r in rows)
    dup_texts = {h: c for h, c in text_hash.items() if c > 1}

    # --- raw category audits (no collapsing) ----------------------------
    ell_raw = Counter(r["ell_status"] for r in rows)
    prompt_raw = Counter(r["prompt_name"] for r in rows)
    score_raw = Counter(r["holistic_essay_score"] for r in rows)
    grade_raw = Counter(r["grade_level"] for r in rows)

    missing_ell = sum(c for v, c in ell_raw.items() if v.strip() == "")
    missing_prompt = sum(c for v, c in prompt_raw.items() if v.strip() == "")
    missing_score = sum(c for v, c in score_raw.items() if v.strip() == "")

    # --- stratum structure on complete cases ----------------------------
    # Complete case = non-missing prompt, holistic score, and ELL status.
    # ELL categories are used exactly as coded; nothing is merged.
    complete = [
        r
        for r in rows
        if r["ell_status"].strip() and r["prompt_name"].strip() and r["holistic_essay_score"].strip()
    ]
    cells: Counter[tuple[str, str, str]] = Counter()
    for r in complete:
        cells[(r["prompt_name"], r["holistic_essay_score"], r["ell_status"])] += 1

    strata: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for (p, y, a), c in cells.items():
        strata[(p, y)][a] += c

    usable, degenerate = {}, {}
    for key, counts in strata.items():
        size = sum(counts.values())
        # usable for permutation: >= 2 units AND >= 2 observed ELL categories
        if size >= 2 and len(counts) >= 2:
            usable[key] = counts
        else:
            degenerate[key] = counts

    usable_sizes = sorted(sum(c.values()) for c in usable.values())
    n_usable_units = sum(usable_sizes)
    minority_share = [
        min(c.values()) / sum(c.values()) for c in usable.values()
    ]

    # --- write full tables ----------------------------------------------
    OUT.mkdir(parents=True, exist_ok=True)
    ell_categories = sorted({a for (_, _, a) in cells})

    with (OUT / "cells.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prompt_name", "holistic_score", "ell_status", "n"])
        for (p, y, a), c in sorted(cells.items()):
            w.writerow([p, y, a, c])

    with (OUT / "strata.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["prompt_name", "holistic_score", "n_total"]
            + [f"n_ell_{a}" for a in ell_categories]
            + ["n_categories", "usable", "minority_share"]
        )
        for (p, y), counts in sorted(strata.items()):
            size = sum(counts.values())
            is_usable = size >= 2 and len(counts) >= 2
            w.writerow(
                [p, y, size]
                + [counts.get(a, 0) for a in ell_categories]
                + [
                    len(counts),
                    is_usable,
                    round(min(counts.values()) / size, 4) if is_usable else "",
                ]
            )

    summary = {
        "source": {
            "repository": "https://github.com/scrosseye/persuade_corpus_2.0",
            "files": [
                "persuade_train.csv (Google Drive id 13phHyDzIsb0MHyJr6q-B-qIa9P2tM135)",
                "persuade_corpus_2.0_test.csv (from persuade_test.zip, Google Drive id 1K1SIJiG-2zWgMlTzxQeYOcLwOsFaVel1)",
            ],
            "sha256": {
                "persuade_train.csv": "f61319edd8bf16a982711ea0399fad59c05afaec05cdf0767f16a2c05c467e23",
                "persuade_test.zip": "51c907f90b1303d610e8fcd8c0cbf3656ec88116bc34b60b93794affa77facb2",
            },
            "license": "CC BY-NC-SA 4.0",
            "citation": "Crossley et al. (2024), Assessing Writing 61, PERSUADE 2.0",
            "downloaded": "2026-08-25",
        },
        "essays": {
            "total": n_total,
            "unique_essay_id_comp": len(id_comp),
            "duplicated_essay_id_comp": sum(1 for c in id_comp.values() if c > 1),
            "unique_excel_mangled_essay_id": len(id_raw),
            "duplicate_full_text_groups": len(dup_texts),
            "essays_in_duplicate_text_groups": sum(dup_texts.values()),
            "writer_id_column_present": False,
        },
        "prompts": {"count": len(prompt_raw), "names": sorted(prompt_raw)},
        "holistic_score_distribution": dict(sorted(score_raw.items())),
        # Exact raw encodings, nothing collapsed.  Note the TWO distinct
        # missing encodings: '' (mostly provider 'Georgia Virtual') and a
        # single space ' ' (provider 'Indiana').
        "ell_status_raw": {repr(v): c for v, c in sorted(ell_raw.items())},
        "missingness": {
            "ell_status": {"n": missing_ell, "prop": round(missing_ell / n_total, 4)},
            "prompt_name": {"n": missing_prompt, "prop": round(missing_prompt / n_total, 4)},
            "holistic_essay_score": {"n": missing_score, "prop": round(missing_score / n_total, 4)},
        },
        "grade_level_raw": {repr(v): c for v, c in sorted(grade_raw.items())},
        "complete_cases": len(complete),
        "strata": {
            "total": len(strata),
            "usable_ge2_units_ge2_categories": len(usable),
            "degenerate_constant_attribute_or_singleton": len(degenerate),
            "units_in_usable_strata": n_usable_units,
            "units_lost_to_degenerate_strata": len(complete) - n_usable_units,
            "usable_size_min": usable_sizes[0],
            "usable_size_median": st.median(usable_sizes),
            "usable_size_mean": round(st.mean(usable_sizes), 1),
            "usable_size_max": usable_sizes[-1],
            "minority_share_min": round(min(minority_share), 4),
            "minority_share_median": round(st.median(minority_share), 4),
            "minority_share_max": round(max(minority_share), 4),
        },
    }
    (OUT / "feasibility.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
