#!/usr/bin/env python
"""Civil Comments additional audit -- Stage 1 non-dataset smoke test.

Runs Detoxify-original (frozen checkpoint, frozen environment) on a tiny
set of SYNTHETIC strings that are NOT drawn from the Civil Comments
dataset, verifying only the software path before any dataset comment is
scored.  Outputs are recorded in a technical log
(``results/civil_comments/smoke_test.json``) and are never used in any
scientific analysis.

Checks (frozen plan section 7, config ``evaluator``):

* checkpoint file hash matches the frozen SHA-256 before loading;
* tokenizer/config cache files match their frozen SHA-256s;
* model loads via ``detoxify.Detoxify`` from the local checkpoint with
  the local HF cache in offline mode (no network, no generic pipeline);
* prediction returns exactly the six expected heads incl. ``toxicity``;
* every output is finite and in [0, 1];
* repeated inference on the same batch is bitwise deterministic;
* tokenizer truncates at ``model_max_length == 512``;
* the scoring path is ``detoxify.detoxify.Detoxify.predict`` (sigmoid
  over logits), not a Hugging Face pipeline.

Run with the frozen scoring environment:

    HF_HOME=data/civil_comments/hf_cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        .venv-cc/bin/python scripts/civil_comments_smoke.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CHECKPOINT = REPO / "data" / "civil_comments" / "checkpoints" / "toxic_original-c1212f89.ckpt"
CHECKPOINT_SHA256 = "c1212f89ac23307ab33932ce29dc446a6e030fb3f384a500890bbe662b7b544a"

HF_SNAPSHOT = (
    REPO / "data" / "civil_comments" / "hf_cache" / "hub" / "models--bert-base-uncased"
    / "snapshots" / "86b5e0934494bd15c9632b12f734a8a67f723594"
)
TOKENIZER_SHA256 = {
    "config.json": "7160e1553ad2ca51d8c1cb066be533db31826e12d173824c1bb0cb1a4f187d20",
    "tokenizer_config.json": "a025160ef0431f1a392f6f050c1310f4c5d9fb6f275932dbccba73c4d214bf10",
    "tokenizer.json": "ce64fce797c24f68df90b40a3f74f579b336a493db14bd583fd520ea0d8c9a98",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}

EXPECTED_HEADS = {"toxicity", "severe_toxicity", "obscene", "threat", "insult", "identity_attack"}

#: Synthetic, NOT from the dataset.  Used only to exercise the software path.
SYNTHETIC = [
    "",
    "This is a neutral test sentence.",
    "You are awful.",
    "word " * 2000,  # forces 512-token truncation
]

OUT = REPO / "results" / "civil_comments" / "smoke_test.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    import os

    log: dict[str, object] = {
        "stage": "1 (non-dataset smoke test)",
        "purpose": "software-path verification only; outputs NEVER used scientifically",
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "packages": {
                p: pkg_version(p)
                for p in (
                    "detoxify", "torch", "transformers", "tokenizers",
                    "sentencepiece", "safetensors", "huggingface-hub", "numpy",
                )
            },
            "env_vars": {
                k: os.environ.get(k)
                for k in ("HF_HOME", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
            },
        },
    }

    failures: list[str] = []

    # -- frozen artifact hashes -------------------------------------------
    ck = sha256_file(CHECKPOINT)
    log["checkpoint_sha256"] = ck
    if ck != CHECKPOINT_SHA256:
        failures.append(f"checkpoint hash mismatch: {ck}")
    tok_hashes = {}
    for name, want in TOKENIZER_SHA256.items():
        got = sha256_file(HF_SNAPSHOT / name)
        tok_hashes[name] = got
        if got != want:
            failures.append(f"tokenizer file hash mismatch: {name} = {got}")
    log["tokenizer_sha256"] = tok_hashes
    if failures:
        log["failures"] = failures
        OUT.write_text(json.dumps(log, indent=2) + "\n")
        raise SystemExit("STOP: frozen hash verification failed:\n" + "\n".join(failures))

    # -- model load via the frozen path -----------------------------------
    import numpy as np
    import torch
    from detoxify import Detoxify
    from detoxify.detoxify import Detoxify as DetoxifyPathCheck

    assert Detoxify is DetoxifyPathCheck, "scoring class is not detoxify.detoxify.Detoxify"

    model = Detoxify(model_type="original", checkpoint=str(CHECKPOINT), device="cpu")
    log["scoring_path"] = f"{type(model).__module__}.{type(model).__qualname__}.predict"
    log["model_class"] = type(model.model).__name__
    log["tokenizer_class"] = type(model.tokenizer).__name__
    log["class_names"] = list(model.class_names)
    log["model_max_length"] = int(model.tokenizer.model_max_length)
    log["torch_default_dtype"] = str(torch.get_default_dtype())
    log["model_param_dtype"] = str(next(model.model.parameters()).dtype)
    log["device"] = str(next(model.model.parameters()).device)

    if set(model.class_names) != EXPECTED_HEADS:
        failures.append(f"unexpected heads: {model.class_names}")
    if "toxicity" not in model.class_names:
        failures.append("missing 'toxicity' head")
    if model.tokenizer.model_max_length != 512:
        failures.append(f"model_max_length != 512: {model.tokenizer.model_max_length}")
    if type(model.model).__name__ != "BertForSequenceClassification":
        failures.append(f"unexpected model class: {type(model.model).__name__}")
    if type(model.tokenizer).__name__ != "BertTokenizer":
        failures.append(f"unexpected tokenizer class: {type(model.tokenizer).__name__}")

    # -- truncation behaviour ----------------------------------------------
    enc = model.tokenizer(SYNTHETIC, truncation=True, padding=True)
    lengths = [len(ids) for ids in enc["input_ids"]]
    log["tokenized_lengths_padded"] = lengths
    if max(lengths) != 512:
        failures.append(f"long synthetic string did not truncate to 512: {lengths}")

    # -- prediction, ranges, determinism -----------------------------------
    r1 = model.predict(SYNTHETIC)
    r2 = model.predict(SYNTHETIC)
    log["outputs_run1"] = {k: [repr(float(v)) for v in vs] for k, vs in r1.items()}
    log["outputs_run2_identical_bitwise"] = r1 == r2
    if r1 != r2:
        failures.append("repeated inference not deterministic")
    for head, vals in r1.items():
        arr = np.asarray(vals, dtype=np.float64)
        if not np.all(np.isfinite(arr)):
            failures.append(f"non-finite output in head {head}")
        if arr.min() < 0.0 or arr.max() > 1.0:
            failures.append(f"output outside [0,1] in head {head}")

    # single-string vs batch path returns same head set
    r_single = model.predict("This is a neutral test sentence.")
    if set(r_single) != EXPECTED_HEADS:
        failures.append("single-string prediction heads differ")

    log["failures"] = failures
    log["passed"] = not failures
    OUT.write_text(json.dumps(log, indent=2) + "\n")
    print(json.dumps({"passed": log["passed"], "failures": failures}, indent=2))
    if failures:
        raise SystemExit("STOP: smoke test failed")
    print(f"technical log written to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
