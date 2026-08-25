"""Independent-writing-only feasibility for the revised primary design.

Pre-data design revision (2026-08-25, before any judge scoring): the primary
experiment is restricted to Independent-task prompts because the canonical
source passages for Text-dependent prompts are not distributed with the
corpus, so an LLM judge cannot apply the source-based holistic rubric the
human raters applied.  Source-based prompts may appear only in clearly
labelled exploratory analyses.

Outputs: results/persuade_feasibility_independent/{strata.csv,cells.csv,
feasibility.json,strata_compact.txt}
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
OUT = ROOT / "results" / "persuade_feasibility_independent"
TASK = "Independent"


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    rows = list(csv.DictReader(DATA.open(newline="", encoding="utf-8")))
    ind = [r for r in rows if r["task"] == TASK]

    prompts_all = sorted({r["prompt_name"] for r in ind})
    complete = [
        r for r in ind
        if r["ell_status"].strip() and r["prompt_name"].strip()
        and r["holistic_essay_score"].strip()
    ]
    ell = Counter(r["ell_status"] for r in complete)
    score = Counter(r["holistic_essay_score"] for r in complete)

    cells: Counter[tuple[str, str, str]] = Counter()
    for r in complete:
        cells[(r["prompt_name"], r["holistic_essay_score"], r["ell_status"])] += 1
    strata: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for (p, y, a), c in cells.items():
        strata[(p, y)][a] += c

    usable = {k: v for k, v in strata.items()
              if sum(v.values()) >= 2 and len(v) >= 2}
    degenerate = {k: v for k, v in strata.items() if k not in usable}
    sizes = sorted(sum(v.values()) for v in usable.values())
    minority = [min(v.values()) / sum(v.values()) for v in usable.values()]
    thin = sum(1 for v in usable.values() if min(v.values()) < 5)

    OUT.mkdir(parents=True, exist_ok=True)
    ell_cats = sorted({a for (_, _, a) in cells})
    with (OUT / "cells.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prompt_name", "holistic_score", "ell_status", "n"])
        for (p, y, a), c in sorted(cells.items()):
            w.writerow([p, y, a, c])
    with (OUT / "strata.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prompt_name", "holistic_score", "n_total"]
                   + [f"n_ell_{a}" for a in ell_cats]
                   + ["n_categories", "usable", "minority_share"])
        for (p, y), v in sorted(strata.items()):
            size = sum(v.values())
            ok = (p, y) in usable
            w.writerow([p, y, size] + [v.get(a, 0) for a in ell_cats]
                       + [len(v), ok,
                          round(min(v.values()) / size, 4) if ok else ""])

    summary = {
        "task_filter": TASK,
        "reason": "source passages for Text-dependent prompts are not in the canonical corpus; LLM judge cannot apply the source-based rubric the human raters applied",
        "independent_prompts_total": len(prompts_all),
        "independent_prompts": prompts_all,
        "essays_independent_total": len(ind),
        "essays_complete_ell": len(complete),
        "ell_counts": dict(sorted(ell.items())),
        "ell_prevalence_complete": round(ell.get("Yes", 0) / len(complete), 4),
        "holistic_score_distribution": dict(sorted(score.items())),
        "strata_total": len(strata),
        "strata_usable": len(usable),
        "strata_degenerate": len(degenerate),
        "strata_thin_minority_lt5": thin,
        "units_in_usable_strata": sum(sizes),
        "ell_in_usable_strata": sum(v.get("Yes", 0) for v in usable.values()),
        "units_lost_to_degenerate": len(complete) - sum(sizes),
        "usable_size_min": sizes[0],
        "usable_size_median": st.median(sizes),
        "usable_size_mean": round(st.mean(sizes), 1),
        "usable_size_max": sizes[-1],
        "minority_share_min": round(min(minority), 4),
        "minority_share_median": round(st.median(minority), 4),
        "minority_share_max": round(max(minority), 4),
        "prompts_with_usable_strata": len({p for (p, _) in usable}),
    }
    (OUT / "feasibility.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    lines = []
    hdr = f"{'prompt':40s}" + "".join(f"{'Y='+str(s):>13s}" for s in range(1, 7)) + f"{'total':>9s}"
    lines.append(hdr); lines.append("-" * len(hdr))
    for p in prompts_all:
        cellstr, tot = [], 0
        for s2 in range(1, 7):
            v = strata.get((p, str(s2)))
            if v is None:
                cellstr.append(f"{'-':>13s}"); continue
            size = sum(v.values()); tot += size
            mark = "" if (p, str(s2)) in usable else "*"
            cellstr.append(f"{size:>6d}/{v.get('Yes',0):>4d}{mark:1s} ")
        lines.append(f"{p[:39]:40s}" + "".join(cellstr) + f"{tot:>9d}")
    lines.append("")
    lines.append("cell format: n_total/n_ELL_Yes ; * = not usable; - = absent")
    (OUT / "strata_compact.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
