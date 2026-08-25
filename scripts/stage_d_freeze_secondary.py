"""Stage D (secondary cells): freeze scoring outcomes BEFORE any attribute join.

Same procedure as the primary Stage D, applied to one secondary cell:
1. verify exactly one final record per manifest essay;
2. write the immutable score-only file (essay ID + judge score ONLY);
3. freeze the raw store (checksum manifest) and hash everything;
4. record completion statistics, token counts (thinking tokens separately
   where the provider bills them), failures, retries, cost.

Usage: stage_d_freeze_secondary.py --cell {haiku_plain,gemini_plain,gpt_ignore}
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.storage import RawScoreStore

CONFIG = json.loads((ROOT / "config" / "preregistered.json").read_text())

# prices per MTok, from the frozen preregistration (verified 2026-08-25)
CELLS = {
    "haiku_plain": {
        "model": CONFIG["judge"]["secondary"][0]["model_id"],
        "condition": "plain",
        "store": "secondary_haiku_plain",
        "price_in": 1.00, "price_out": 5.00,
        "thinking_billed_as_output": False,
    },
    "gemini_plain": {
        "model": CONFIG["judge"]["secondary"][1]["model_id"],
        "condition": "plain",
        "store": "secondary_gemini_plain",
        "price_in": 0.75, "price_out": 3.75,
        "thinking_billed_as_output": True,
    },
    "gpt_ignore": {
        "model": CONFIG["api_parameters"]["model"],
        "condition": "ignore_demographics",
        "store": "secondary_gpt_ignore",
        "price_in": 0.75, "price_out": 4.50,
        "thinking_billed_as_output": False,
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, choices=sorted(CELLS))
    args = ap.parse_args()
    cell = CELLS[args.cell]
    model, condition = cell["model"], cell["condition"]
    store_dir = ROOT / "data" / "scoring" / cell["store"]

    manifest_ids = {
        r["essay_id_comp"]
        for r in csv.DictReader((ROOT / "data" / "scoring" / "primary_sample_manifest.csv").open())
    }
    raw_file = store_dir / f"scores__{model}__{condition}.jsonl"
    records = [json.loads(line) for line in raw_file.open(encoding="utf-8")]

    ids = [r["essay_id_comp"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate records"
    assert set(ids) == manifest_ids, (
        f"records != manifest: missing {len(manifest_ids - set(ids))}, "
        f"extra {len(set(ids) - manifest_ids)}"
    )

    valid = [r for r in records if r["parsed_score"] is not None]
    invalid = [r for r in records if r["parse_error"]]
    tech_fail = [r for r in records if r["error_status"]]
    assert len(valid) + len(invalid) + len(tech_fail) == len(records)

    score_only = store_dir / "scores_only.csv"
    with score_only.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["essay_id_comp", "judge_score"])
        for r in sorted(valid, key=lambda r: r["essay_id_comp"]):
            w.writerow([r["essay_id_comp"], r["parsed_score"]])

    store = RawScoreStore(store_dir)
    if not store.is_frozen():
        store.freeze()
    store.verify_frozen()

    tokens_in = sum(r["prompt_tokens"] for r in records)
    tokens_out = sum(r["completion_tokens"] for r in records)
    tokens_think = sum(r.get("thinking_tokens", 0) for r in records)
    billed_out = tokens_out + (tokens_think if cell["thinking_billed_as_output"] else 0)
    cost = tokens_in / 1e6 * cell["price_in"] + billed_out / 1e6 * cell["price_out"]
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    summary = {
        "stage": "D-secondary",
        "cell": args.cell,
        "model": model,
        "condition": condition,
        "n_manifest": len(manifest_ids),
        "n_records": len(records),
        "n_valid_scores": len(valid),
        "n_invalid_responses": len(invalid),
        "n_technical_failures": len(tech_fail),
        "retries_total": sum(r["retry_count"] for r in records),
        "records_with_retries": sum(1 for r in records if r["retry_count"]),
        "provider_model_strings": sorted({r["provider_model"] for r in records}),
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "thinking_tokens": tokens_think,
        "thinking_billed_as_output": cell["thinking_billed_as_output"],
        "actual_cost_usd": round(cost, 2),
        "sha256": {
            raw_file.name: sha(raw_file),
            "scores_only.csv": sha(score_only),
            "FROZEN.json": sha(store_dir / "FROZEN.json"),
        },
    }
    (store_dir / "stage_d_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
