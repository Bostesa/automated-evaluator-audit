"""Stage E (secondary cells): run each preregistered secondary confirmatory
analysis exactly once, with its frozen seed slot.

Usage: stage_e_secondary.py --cell {haiku_plain,gemini_plain,gpt_ignore}

Identical analysis path to the primary (run_primary_analysis): frozen-store
gate, preregistered exclusion rule, demographics joined only post-freeze,
native 1..6 score space, exact (prompt, human score) strata, conditional G2
with B=999 within-stratum permutations plus the two companion statistics on
the same draws, and the preregistered descriptive diagnostics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.analysis import run_primary_analysis

CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())

CELLS = {
    "haiku_plain": {
        "model": CONFIG["judge"]["secondary"][0]["model_id"],
        "condition": "plain",
        "store": "secondary_haiku_plain",
        "seed_slot": tuple(CONFIG["seed_slots"]["secondary_judge_1_plain"]),
    },
    "gemini_plain": {
        "model": CONFIG["judge"]["secondary"][1]["model_id"],
        "condition": "plain",
        "store": "secondary_gemini_plain",
        "seed_slot": tuple(CONFIG["seed_slots"]["secondary_judge_2_plain"]),
    },
    "gpt_ignore": {
        "model": CONFIG["api_parameters"]["model"],
        "condition": "ignore_demographics",
        "store": "secondary_gpt_ignore",
        "seed_slot": tuple(CONFIG["seed_slots"]["primary_judge_ignore_demographics"]),
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, choices=sorted(CELLS))
    args = ap.parse_args()
    cell = CELLS[args.cell]

    out = ROOT / "results" / f"secondary_{args.cell}_analysis.json"
    if out.exists():
        raise SystemExit(
            f"{out} already exists: each secondary confirmatory cell is "
            "analysed exactly once; refusing to re-run"
        )

    result = run_primary_analysis(
        ROOT / "data" / "scoring" / cell["store"],
        ROOT / "data" / "persuade" / "persuade_essay_level.csv",
        judge=cell["model"],
        condition=cell["condition"],
        n_permutations=CONFIG["analysis"]["n_permutations"],
        permutation_seed=CONFIG["permutation_seed"],
        seed_slot=cell["seed_slot"],
    )
    result.report["family"] = "secondary_confirmatory"
    result.report["seed_slot"] = list(cell["seed_slot"])
    result.write(out)
    print(json.dumps({k: v for k, v in result.report.items() if k != "exclusions"},
                     indent=2))


if __name__ == "__main__":
    main()
