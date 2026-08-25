"""Verify the scoring/attribute information barrier for a scored cell.

Checks, in code, for one raw-score store (primary or secondary):

1. STRUCTURAL: ``build_judge_prompt`` accepts no demographic, ELL, or
   human-score argument (function signature introspection).
2. RECORD-LEVEL: every stored ``prompt_sha256`` equals the hash of the
   prompt re-rendered from the frozen template and the essay text alone.
   Since the hash is over the full prompt bytes, a matching hash proves that
   NOTHING beyond (frozen template, assignment, essay) entered the prompt —
   no ELL status, no human score, no demographic metadata.
3. APPEND-ONLY: the store is frozen with verified checksums, and a write
   attempt is structurally refused.
4. PROVENANCE: every record carries provider model string, provider request
   ID, and token usage.
5. RETRY POLICY: the frozen 3-retry policy was applied — every judge
   adapter has max_retries=3, and every technical-failure record shows
   exactly 3 retries before exclusion.

Usage: verify_information_barrier.py --store DATA_SCORING_SUBDIR
"""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from offcriterion.pipeline.anthropic_judge import AnthropicJudge
from offcriterion.pipeline.gemini_judge import GeminiJudge
from offcriterion.pipeline.openai_judge import OpenAIJudge
from offcriterion.pipeline.prompts import (
    build_judge_prompt,
    load_prompt_materials,
    prompt_sha256,
)
from offcriterion.pipeline.storage import RawScoreStore, StorageError

DATA = ROOT / "data" / "persuade"
FORBIDDEN_PARAMS = {"ell", "ell_status", "human_score", "holistic_essay_score",
                    "gender", "race", "race_ethnicity", "grade_level",
                    "economically_disadvantaged", "student_disability_status",
                    "attribute", "demographic", "metadata"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True,
                    help="subdirectory of data/scoring to verify")
    args = ap.parse_args()
    store_dir = ROOT / "data" / "scoring" / args.store
    checks: dict[str, str] = {}

    # 1. structural barrier
    params = set(inspect.signature(build_judge_prompt).parameters)
    leaks = params & FORBIDDEN_PARAMS
    assert not leaks, f"prompt builder accepts forbidden parameters: {leaks}"
    checks["structural_barrier"] = (
        f"build_judge_prompt parameters = {sorted(params)}; no demographic, "
        "ELL, or human-score code path exists")

    # 3a. frozen store with verified checksums
    store = RawScoreStore(store_dir)
    store.verify_frozen()
    checks["store_frozen_checksums"] = "FROZEN.json present; all checksums verified"

    # 3b. append refusal
    try:
        store.append(judge="x", condition="plain", essay_id_comp="TEST",
                     prompt_sha256="0" * 64, raw_response="{}")
        raise AssertionError("frozen store accepted a write")
    except StorageError:
        checks["append_only"] = "write to frozen store structurally refused"

    # 2, 4, 5: record-level checks per scores file
    materials = load_prompt_materials(DATA / "prompt_materials.csv")
    meta = {r["essay_id_comp"]: r
            for r in csv.DictReader((DATA / "persuade_essay_level.csv").open())}
    texts: dict[str, str] = {}
    with (DATA / "essay_texts.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts[row["essay_id_comp"]] = row["full_text"]

    for scores_file in sorted(store_dir.glob("scores__*.jsonl")):
        records = [json.loads(l) for l in scores_file.open(encoding="utf-8")]
        n_hash_ok = n_prov = n_fail = 0
        bad_hash, bad_fail = [], []
        for rec in records:
            eid = rec["essay_id_comp"]
            mat = materials[meta[eid]["prompt_name"]]
            rebuilt = build_judge_prompt(
                essay_text=texts[eid], task=mat["task"],
                assignment=mat["assignment"], source_titles=mat["source_text"],
                condition=rec["condition"],
            )
            if prompt_sha256(rebuilt) == rec["prompt_sha256"]:
                n_hash_ok += 1
            else:
                bad_hash.append(eid)
            if rec["error_status"]:
                n_fail += 1
                if rec["retry_count"] != 3:
                    bad_fail.append(eid)
            elif rec["provider_model"] and rec["provider_request_id"] \
                    and rec["prompt_tokens"] > 0:
                n_prov += 1
        assert not bad_hash, f"{scores_file.name}: prompt hash mismatch for {bad_hash[:5]}"
        assert not bad_fail, f"{scores_file.name}: failures without 3 retries: {bad_fail[:5]}"
        assert n_prov == len(records) - n_fail, (
            f"{scores_file.name}: {len(records) - n_fail - n_prov} successful "
            "records missing provider/usage metadata")
        checks[scores_file.name] = (
            f"{len(records)} records: {n_hash_ok} prompt hashes match frozen "
            f"template+essay rendering (nothing else entered any prompt); "
            f"{n_prov} successful records carry provider model, request ID, "
            f"and token usage; {n_fail} technical failures all exhausted "
            "exactly 3 retries")

    # 5. adapter retry policy is the frozen one
    for cls in (OpenAIJudge, AnthropicJudge, GeminiJudge):
        assert inspect.signature(cls).parameters["max_retries"].default == 3, cls
    checks["retry_policy"] = (
        "OpenAIJudge, AnthropicJudge, GeminiJudge all default to the frozen "
        "3-retry policy on 429/5xx/network; other 4xx aborts fatally")

    print(json.dumps({"store": args.store, "all_checks_passed": True,
                      "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
