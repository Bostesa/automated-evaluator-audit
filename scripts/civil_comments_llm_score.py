#!/usr/bin/env python
"""Civil Comments LLM-evaluator extension -- attribute-blind toxicity scoring.

Scores the frozen one-comment-per-article primary manifest (N = 69,573) with
one of the three frozen LLM evaluators, exactly as frozen in
``config/civil_comments_llm_evaluator_addendum.json``:

* manifest and dataset hashes verified before reading;
* ONLY ``id`` and ``comment_text`` are read from the source table -- no
  identity column, no human toxicity label, no article field, no Detoxify
  score is ever materialised in this process (attribute-blind by
  construction);
* the frozen rubric template renders a prompt byte-identical across
  providers; per-item rendered-prompt SHA-256 is recorded;
* requests in ascending integer comment-id order, 10 worker threads;
* append-only RawScoreStore per provider; resumption may only fill comment
  ids absent from the store (every existing record is FINAL);
* frozen retry policy (3 retries on 429/5xx/network; other 4xx fatal);
  post-retry failure = technical exclusion; unparseable response =
  exclusion; no repair, no reprompt, no selective re-scoring.

Modes:
    --estimate            A-blind token/cost estimate; no API call
    --smoke               8 fixed NON-DATASET sentences; verifies credentials,
                          exact model availability, and structured output
    (default)             score the frozen manifest
    --freeze              verify coverage, classify records, report pooled
                          A-blind stats, SHA-256-freeze the store

Run:  .venv/bin/python scripts/civil_comments_llm_score.py \
          --provider {gpt,claude,gemini} --key-file PATH [mode]
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from offcriterion.pipeline.cc_toxicity_judges import (  # noqa: E402
    CCAnthropicJudge,
    CCGeminiJudge,
    CCOpenAIJudge,
    ParseError,
    parse_toxicity_score,
)
from offcriterion.pipeline.openai_judge import FatalAPIError  # noqa: E402
from offcriterion.pipeline.prompts import prompt_sha256  # noqa: E402
from offcriterion.pipeline.storage import RawScoreStore  # noqa: E402

CONFIG = json.loads(
    (REPO / "config" / "civil_comments_llm_evaluator_addendum.json").read_text()
)
DATASET_CSV = REPO / "data" / "civil_comments" / "all_data_with_identities.csv"
DATASET_SHA256 = CONFIG["parent_freezes"]["dataset_sha256"]
MANIFEST = REPO / CONFIG["parent_freezes"]["primary_manifest"]
MANIFEST_SHA256 = CONFIG["parent_freezes"]["primary_manifest_sha256"]
TEMPLATE = REPO / CONFIG["prompt"]["file"]
TEMPLATE_SHA256 = CONFIG["prompt"]["template_sha256"]
N_EXPECTED = CONFIG["sample"]["n_expected"]
WORKERS = 10
CONDITION = "cc_toxicity"

PROVIDERS = {
    "gpt": (CCOpenAIJudge, CONFIG["evaluators"]["gpt"]["model_id"]),
    "claude": (CCAnthropicJudge, CONFIG["evaluators"]["claude"]["model_id"]),
    "gemini": (CCGeminiJudge, CONFIG["evaluators"]["gemini"]["model_id"]),
}

# Fixed NON-DATASET smoke sentences (invented; not drawn from any corpus row).
SMOKE_SENTENCES = [
    "The library reopens on Tuesday after the renovation.",
    "I completely disagree with the council's new parking plan.",
    "You clearly didn't read the article before commenting.",
    "That was a thoughtful and well-argued response, thank you.",
    "This is the dumbest take I have seen all week.",
    "The recipe needs more salt and a longer baking time.",
    "Anyone who believes this nonsense should be ashamed of themselves.",
    "Great photo! Where was it taken?",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_template() -> str:
    if sha256_file(TEMPLATE) != TEMPLATE_SHA256:
        raise SystemExit("STOP: rubric template hash mismatch")
    return TEMPLATE.read_text(encoding="utf-8")


def render(template: str, comment_text: str) -> str:
    if "[[COMMENT_TEXT]]" not in template:
        raise SystemExit("STOP: template placeholder missing")
    return template.replace("[[COMMENT_TEXT]]", comment_text)


def manifest_ids() -> list[str]:
    if sha256_file(MANIFEST) != MANIFEST_SHA256:
        raise SystemExit("STOP: primary manifest hash mismatch")
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        ids = [r["comment_id"] for r in csv.DictReader(f)]
    if len(ids) != N_EXPECTED or len(set(ids)) != N_EXPECTED:
        raise SystemExit("STOP: manifest id count mismatch")
    return sorted(ids, key=int)


def load_texts(wanted: set[str]) -> dict[str, str]:
    """Read ONLY (id, comment_text), attribute-blind, hash-verified."""
    if sha256_file(DATASET_CSV) != DATASET_SHA256:
        raise SystemExit("STOP: dataset hash mismatch")
    texts: dict[str, str] = {}
    with DATASET_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] in wanted:
                texts[row["id"]] = row["comment_text"]
    if set(texts) != wanted:
        raise SystemExit("STOP: manifest ids missing from dataset")
    return texts


def store_dir(provider: str) -> Path:
    return REPO / "data" / "scoring" / f"cc_{provider}_toxicity"


def score_file(provider: str, model: str) -> Path:
    return store_dir(provider) / f"scores__{model}__{CONDITION}.jsonl"


def estimate(provider: str, model: str) -> None:
    template = load_template()
    ids = manifest_ids()
    texts = load_texts(set(ids))
    overhead = len(render(template, ""))
    total_chars = sum(len(t) for t in texts.values())
    # A-blind heuristic: ~4 characters per token for English prose.
    in_tok = (total_chars + overhead * len(ids)) / 4
    out_tok = 8 * len(ids)  # {"score": n}
    price = json.loads((REPO / "config" / "preregistered.json").read_text())
    table = {
        "gpt": price["judge"]["primary"]["pricing_per_mtok"],
        "claude": price["judge"]["secondary"][0]["pricing_per_mtok"],
        "gemini": price["judge"]["secondary"][1]["pricing_per_mtok"],
    }[provider]
    thinking = 100 * len(ids) if provider == "gemini" else 0
    cost = (in_tok * table["input"] + (out_tok + thinking) * table["output"]) / 1e6
    print(json.dumps({
        "provider": provider, "model": model, "n_comments": len(ids),
        "estimated_input_tokens": round(in_tok),
        "estimated_output_tokens": out_tok,
        "assumed_thinking_tokens": thinking,
        "pricing_per_mtok": table,
        "estimated_cost_usd": round(cost, 2),
        "note": "informational only; never changes the frozen evaluator family",
    }, indent=2))


def freeze(provider: str, model: str) -> None:
    ids = manifest_ids()
    path = score_file(provider, model)
    if not path.exists():
        raise SystemExit("STOP: no score store to freeze")
    records: dict[str, dict] = {}
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        cid = rec["essay_id_comp"]
        if cid in records:
            raise SystemExit(f"STOP: duplicate record for comment {cid}")
        records[cid] = rec
    missing = [i for i in ids if i not in records]
    extra = [i for i in records if i not in set(ids)]
    if missing or extra:
        raise SystemExit(f"STOP: coverage mismatch: {len(missing)} missing, {len(extra)} extra")
    dist = {str(s): 0 for s in range(1, 6)}
    n_ok = n_tech = n_invalid = 0
    in_tok = out_tok = think_tok = 0
    for rec in records.values():
        in_tok += rec.get("prompt_tokens", 0)
        out_tok += rec.get("completion_tokens", 0)
        think_tok += rec.get("thinking_tokens", 0)
        if rec.get("error_status"):
            n_tech += 1
        elif rec.get("parsed_score") is None:
            n_invalid += 1
        else:
            n_ok += 1
            dist[str(rec["parsed_score"])] += 1
    store = RawScoreStore(store_dir(provider))
    if not store.is_frozen():
        store.freeze()
    store.verify_frozen()
    price = {
        "gpt": (0.75, 4.5), "claude": (1.0, 5.0), "gemini": (0.75, 3.75),
    }[provider]
    meta = {
        "stage": "LLM score-store freeze (pooled A-blind quantities only)",
        "provider": provider,
        "model_id": model,
        "n_expected": N_EXPECTED,
        "n_records": len(records),
        "n_ok": n_ok,
        "n_technical_failures": n_tech,
        "n_invalid_responses": n_invalid,
        "exclusion_rate": round((n_tech + n_invalid) / len(records), 6),
        "pooled_score_distribution": dist,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "thinking_tokens": think_tok,
        "actual_cost_usd": round((in_tok * price[0] + (out_tok + think_tok) * price[1]) / 1e6, 2),
        "note_gemini_billing": "thinking tokens are billed as output; both included in cost",
        "score_store_sha256": sha256_file(path),
        "store_frozen_manifest": str((store_dir(provider) / "FROZEN.json").relative_to(REPO)),
    }
    out = REPO / "results" / "civil_comments" / f"llm_scores_{provider}_FROZEN.json"
    out.write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    ap.add_argument("--key-file")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    judge_cls, model = PROVIDERS[args.provider]

    if args.estimate:
        estimate(args.provider, model)
        return
    if args.freeze:
        freeze(args.provider, model)
        return
    if not args.key_file:
        raise SystemExit("--key-file required for API modes")
    key = Path(args.key_file).read_text().strip()
    judge = judge_cls(api_key=key, model=model)
    template = load_template()

    if args.smoke:
        for i, sentence in enumerate(SMOKE_SENTENCES):
            result = judge.call(render(template, sentence))
            parsed: int | str
            try:
                parsed = parse_toxicity_score(result.raw_content)
            except ParseError as err:
                parsed = f"PARSE-FAIL: {err}"
            print(f"smoke {i}: model={result.provider_model!r} score={parsed} "
                  f"retries={result.retry_count} err={result.error_status!r}")
        return

    ids = manifest_ids()
    texts = load_texts(set(ids))
    store = RawScoreStore(store_dir(args.provider))
    path = score_file(args.provider, model)
    done: set[str] = set()
    prior_failures = 0
    if path.exists():
        for line in path.open(encoding="utf-8"):
            rec = json.loads(line)
            done.add(rec["essay_id_comp"])
            if rec.get("error_status"):
                prior_failures += 1
    todo = [i for i in ids if i not in done]
    print(f"provider={args.provider} model={model}")
    print(f"targets={len(ids)} done={len(done)} "
          f"prior_technical_failures={prior_failures} todo={len(todo)}", flush=True)

    lock = threading.Lock()
    counters = {"ok": 0, "invalid": 0, "tech_fail": 0}
    fatal: list[str] = []

    def work(comment_id: str) -> None:
        if fatal:
            return
        prompt = render(template, texts[comment_id])
        try:
            result = judge.call(prompt)
        except FatalAPIError as err:
            with lock:
                fatal.append(str(err))
            return
        parsed: int | None = None
        parse_error = ""
        if not result.error_status:
            try:
                parsed = parse_toxicity_score(result.raw_content)
            except ParseError as err:
                parse_error = str(err)
        extra = {
            "provider_model": result.provider_model,
            "provider_request_id": result.provider_request_id,
            "parsed_score": parsed,
            "parse_error": parse_error,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "retry_count": result.retry_count,
            "temperature_omitted": result.temperature_omitted,
            "error_status": result.error_status,
        }
        if hasattr(result, "thinking_tokens"):
            extra["thinking_tokens"] = result.thinking_tokens
        if args.provider == "claude":
            extra["seed_supported"] = False
        with lock:
            store.append(
                judge=model, condition=CONDITION,
                essay_id_comp=comment_id, prompt_sha256=prompt_sha256(prompt),
                raw_response=result.raw_content, extra=extra,
            )
            if result.error_status:
                counters["tech_fail"] += 1
            elif parsed is None:
                counters["invalid"] += 1
            else:
                counters["ok"] += 1
            total = sum(counters.values())
            if total % 500 == 0:
                print(f"progress {total}/{len(todo)} {counters}", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, todo))

    if fatal:
        print("FATAL:", fatal[0])
        sys.exit(2)
    print("finished:", counters)


if __name__ == "__main__":
    main()
