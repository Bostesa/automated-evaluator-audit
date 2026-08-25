"""Stage D: freeze scoring outcomes BEFORE any attribute join.

1. Verify exactly one final record per manifest essay under the
   preregistered rules.
2. Write the immutable score-only file (essay ID + judge score ONLY).
3. Freeze the raw store (checksum manifest) and hash everything.
4. Record completion statistics, token counts, failures, retries, cost.

Runs strictly before analysis; ``RawScoreStore.verify_frozen`` is the code
gate that analysis depends on.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.storage import RawScoreStore

MODEL = "gpt-5.4-mini-2026-03-17"
CONDITION = "plain"
STORE = ROOT / "data" / "scoring" / "primary"
PRICE_IN, PRICE_OUT = 0.75, 4.50  # USD per MTok, verified 2026-08-25


def main() -> None:
    manifest_ids = {
        r["essay_id_comp"]
        for r in csv.DictReader((ROOT / "data" / "scoring" / "primary_sample_manifest.csv").open())
    }
    raw_file = STORE / f"scores__{MODEL}__{CONDITION}.jsonl"
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

    score_only = STORE / "primary_scores_only.csv"
    with score_only.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["essay_id_comp", "judge_score"])
        for r in sorted(valid, key=lambda r: r["essay_id_comp"]):
            w.writerow([r["essay_id_comp"], r["parsed_score"]])
    header = score_only.read_text().splitlines()[0]
    assert header == "essay_id_comp,judge_score", header

    store = RawScoreStore(STORE)
    if not store.is_frozen():
        store.freeze()
    store.verify_frozen()

    tokens_in = sum(r["prompt_tokens"] for r in records)
    tokens_out = sum(r["completion_tokens"] for r in records)
    cost = tokens_in / 1e6 * PRICE_IN + tokens_out / 1e6 * PRICE_OUT
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    summary = {
        "stage": "D",
        "model": MODEL,
        "condition": CONDITION,
        "n_manifest": len(manifest_ids),
        "n_records": len(records),
        "n_valid_scores": len(valid),
        "n_invalid_responses": len(invalid),
        "n_technical_failures": len(tech_fail),
        "retries_total": sum(r["retry_count"] for r in records),
        "records_with_retries": sum(1 for r in records if r["retry_count"]),
        "temperature_omitted_any": any(r["temperature_omitted"] for r in records),
        "provider_model_strings": sorted({r["provider_model"] for r in records}),
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "actual_cost_usd": round(cost, 2),
        "sha256": {
            raw_file.name: sha(raw_file),
            "primary_scores_only.csv": sha(score_only),
            "FROZEN.json": sha(STORE / "FROZEN.json"),
        },
    }
    (STORE / "stage_d_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
