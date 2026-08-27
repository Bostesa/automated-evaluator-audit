#!/usr/bin/env python
"""Civil Comments additional audit -- Stage 2 attribute-blind scoring.

Scores the FULL 448,000-comment identity-annotated census with
Detoxify-original exactly as frozen in
``config/civil_comments_additional_audit.json`` (section ``evaluator``):

* dataset hash verified before reading; checkpoint hash verified before
  loading;
* ONLY ``id`` and ``comment_text`` are read from the source table -- no
  identity column, no human toxicity label, no article field is ever
  materialised in this process (attribute-blind by construction);
* input ordering: ascending integer comment id over the full census;
* batching: consecutive batches of 32 in that frozen order;
* evaluator: ``detoxify.detoxify.Detoxify.predict`` (sigmoid path),
  CPU, float32, ``model.eval()``, no grad; frozen local checkpoint and
  local tokenizer cache in offline mode;
* raw continuous ``toxicity`` probabilities stored keyed ONLY by
  comment id, plus per-comment technical status and A-free
  token-length/truncation metadata.

The store is written incrementally in frozen batch order; interrupted
runs resume at the last complete batch boundary, which is exact because
batch composition is frozen and batches are independent.

A batch-level evaluator exception triggers a per-comment retry inside
that batch: comments that still fail are recorded as technical failures
(status ``failed``); comments rescued alone are marked
``ok_singleton_fallback`` so any batching deviation is visible in the
store itself.  No other exclusion or rescoring is permitted.

Run:

    HF_HOME=data/civil_comments/hf_cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        .venv-cc/bin/python scripts/civil_comments_score.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DATASET_CSV = REPO / "data" / "civil_comments" / "all_data_with_identities.csv"
DATASET_SHA256 = "403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f"
DATASET_ROWS = 448_000

CHECKPOINT = REPO / "data" / "civil_comments" / "checkpoints" / "toxic_original-c1212f89.ckpt"
CHECKPOINT_SHA256 = "c1212f89ac23307ab33932ce29dc446a6e030fb3f384a500890bbe662b7b544a"

BATCH_SIZE = 32
OUT = REPO / "results" / "civil_comments" / "scores_raw.csv"
LOG = REPO / "results" / "civil_comments" / "scoring_technical_log.json"

FIELDS = ["comment_id", "toxicity", "status", "n_tokens", "truncated"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_id_text() -> list[tuple[str, str]]:
    """Read ONLY (id, comment_text), attribute-blind, hash-verified."""
    if sha256_file(DATASET_CSV) != DATASET_SHA256:
        raise SystemExit("STOP: dataset hash mismatch")
    pairs: list[tuple[str, str]] = []
    with DATASET_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pairs.append((row["id"], row["comment_text"]))
    if len(pairs) != DATASET_ROWS:
        raise SystemExit(f"STOP: expected {DATASET_ROWS} rows, read {len(pairs)}")
    if len({i for i, _ in pairs}) != len(pairs):
        raise SystemExit("STOP: duplicate comment ids")
    pairs.sort(key=lambda p: int(p[0]))  # frozen ascending-integer ordering
    return pairs


def resume_offset(pairs: list[tuple[str, str]]) -> int:
    """Rows already scored, truncated down to a complete-batch boundary."""
    if not OUT.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)
        return 0
    with OUT.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    if header != FIELDS:
        raise SystemExit("STOP: existing score store has unexpected header")
    keep = (len(body) // BATCH_SIZE) * BATCH_SIZE
    body = body[:keep]
    for k, row in enumerate(body):
        if row[0] != pairs[k][0]:
            raise SystemExit(f"STOP: existing store row {k} id mismatch ({row[0]} != {pairs[k][0]})")
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(body)
    return keep


def main() -> None:
    ck = sha256_file(CHECKPOINT)
    if ck != CHECKPOINT_SHA256:
        raise SystemExit("STOP: checkpoint hash mismatch")

    pairs = read_id_text()
    start = resume_offset(pairs)
    print(f"resuming at row {start} of {len(pairs)}", flush=True)

    from detoxify import Detoxify

    model = Detoxify(model_type="original", checkpoint=str(CHECKPOINT), device="cpu")
    assert "toxicity" in model.class_names
    tok = model.tokenizer

    failures: list[dict[str, str]] = []
    singleton_fallbacks: list[str] = []
    t0 = time.time()
    n_batches_done = 0

    with OUT.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for lo in range(start, len(pairs), BATCH_SIZE):
            batch = pairs[lo : lo + BATCH_SIZE]
            texts = [t for _, t in batch]
            # A-free token metadata under the frozen truncation setting
            enc = tok(texts, truncation=True, padding=False)
            n_tok = [len(ids) for ids in enc["input_ids"]]
            trunc = [n >= 512 for n in n_tok]
            rows_out = []
            try:
                preds = model.predict(texts)["toxicity"]
                for (cid, _), p, n, tr in zip(batch, preds, n_tok, trunc):
                    rows_out.append([cid, repr(float(p)), "ok", n, int(tr)])
            except Exception as batch_err:  # per-comment rescue, logged
                for (cid, text), n, tr in zip(batch, n_tok, trunc):
                    try:
                        p = model.predict(text)["toxicity"]
                        rows_out.append([cid, repr(float(p)), "ok_singleton_fallback", n, int(tr)])
                        singleton_fallbacks.append(cid)
                    except Exception as err:
                        rows_out.append([cid, "", "failed", n, int(tr)])
                        failures.append({"comment_id": cid, "error": f"{type(err).__name__}: {err}",
                                         "batch_error": f"{type(batch_err).__name__}: {batch_err}"})
            writer.writerows(rows_out)
            f.flush()
            n_batches_done += 1
            if n_batches_done % 100 == 0:
                done = lo + len(batch) - start
                rate = done / (time.time() - t0)
                eta_h = (len(pairs) - lo - len(batch)) / rate / 3600 if rate else float("nan")
                print(f"{lo + len(batch)}/{len(pairs)} rows  {rate:.1f} rows/s  eta {eta_h:.2f} h", flush=True)

    LOG.write_text(json.dumps({
        "stage": "2 (attribute-blind scoring)",
        "n_rows": len(pairs),
        "batch_size": BATCH_SIZE,
        "resumed_from_row": start,
        "n_technical_failures": len(failures),
        "technical_failures": failures,
        "n_singleton_fallbacks": len(singleton_fallbacks),
        "singleton_fallbacks": singleton_fallbacks,
        "elapsed_seconds_this_run": round(time.time() - t0, 1),
    }, indent=2) + "\n")
    print("scoring complete", flush=True)


if __name__ == "__main__":
    main()
