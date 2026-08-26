# Reproducing the reported results

This is the stage by stage map of the scientific pipeline, in the order it
actually happened. Every stage lists its script(s), inputs, outputs,
evidentiary status, the git commit that froze it, and whether it touches
an external model API.

No reported number requires an API call to reproduce. All evaluator
outputs are frozen under `data/scoring/` with SHA-256 manifests
(`FROZEN.json`), and every analysis re-runs deterministically from them
(seeded `numpy` `SeedSequence` generators, seeds recorded in
`config/preregistered.json`).

| Marker | Meaning |
|---|---|
| ✅ LOCAL | safe to run, no network, deterministic |
| 💸 **API** | contacts a paid provider API, do not run casually |

## Setup

```bash
pip install -e ".[dev,analysis]"
```

For real data stages, first obtain PERSUADE 2.0 (canonical sources and
SHA-256 in `data/persuade/README.md`) and rebuild the derived inputs:

```bash
python scripts/prepare_persuade.py --out-dir data/persuade   # ✅ LOCAL
```

By default the script writes to `data/persuade/prepared/`, so existing
copies are never overwritten, and it verifies byte exact SHA-256
reproduction of all three derived files.

## Stage map

### 1. Synthetic validation (commit `6ba8331`)
- **Script:** `offcriterion run` (alias `evaluator-audit run`), ✅ LOCAL, ~1 min
- **Inputs:** none (six generative scenarios, root seed 20240817)
- **Outputs:** `results/results.md`, `results.tex`, `rejection_rates.{csv,json}`,
  `diagnostics.json`, `config.json` (all tracked), `replicates.csv` (untracked, regenerable)
- **Status:** validation evidence, frozen before any real scoring

### 2. PERSUADE feasibility, v1, both tasks (commit `7d250c4`, superseded)
- **Scripts:** `persuade_feasibility.py`, `persuade_power_planning.py`,
  `persuade_power_extra.py`, `persuade_fill_report.py`, ✅ LOCAL
- **Outputs:** `results/persuade_feasibility/`, `docs/persuade_feasibility.md`
- **Status:** design stage evidence for the GO decision. Superseded by
  stage 3 for the primary design, retained as the decision record.

### 3. Independent writing revision, v2, the operative design (commit `9343b7f`)
- **Scripts:** `persuade_feasibility_independent.py`, `persuade_power_independent.py`, ✅ LOCAL
- **Outputs:** `results/persuade_feasibility_independent/` (census n = 11,360,
  1,039 ELL, 7 prompts, 31 strata)
- **Status:** design revision made before any scoring, frozen in
  preregistration v2

### 4. Preregistration freeze (commits `5c81d13` v1, `9343b7f` v2, `16c9925` v3)
- **Artifacts:** `docs/preregistration.md`, `config/preregistered.json`,
  `prompts/`, all FROZEN before any evaluator scoring
- All three revisions predate all scoring. The revision log is §21 of the
  preregistration.

### 5. Dry run and information barrier validation (commit `5c81d13`)
- **Script:** `dry_run.py`, ✅ LOCAL (fake deterministic evaluator, no API)
- **Outputs:** `results/dryrun/` (untracked, disposable, no scientific content)

### 6. Stage A: sample freeze (commit `74b9332`)
- **Artifacts:** `data/scoring/primary_sample_manifest.csv`,
  `data/scoring/stage_a_freeze.json` (SHA-256 of the manifest, the
  prompts, the preregistration, and the analysis source files), FROZEN

### 7. Stages B–D: primary scoring (commit `d00044c`) 💸 **API**
- **Script:** `run_primary_scoring.py --key-file …` (GPT-5.4-mini, standard prompt)
- **Outputs:** `data/scoring/primary/`, FROZEN (raw JSONL, SHA-256
  manifest, `stage_d_summary.json`), 10,893 valid scores and 467
  technical exclusions. Smoke store in `data/scoring/smoke/`.
- **Freeze script:** `stage_d_freeze.py` (✅ LOCAL, already executed, the
  store refuses further writes)

### 8. Stage E: preregistered primary analysis + negative control (commit `18524cc`)
- **Scripts:** `stage_e_analysis.py`, `negative_control.py`, ✅ LOCAL
- **Inputs:** frozen `data/scoring/primary/`, `persuade_essay_level.csv`
- **Outputs:** `results/primary_analysis.json` (G² = 420.86, p = 0.001,
  Δ = −0.320), `results/negative_control.json` (p = 0.188)
- **Status:** PREREGISTERED PRIMARY. Re-running reproduces the frozen
  values bit for bit (verified 2026-08-26).
- `stage_e_analysis.py` writes `results/primary_analysis.json` in
  place. The tracked copy is the preregistered record. If you rerun,
  verify that `git diff` is empty rather than committing a regenerated
  file.

### 9. Secondary scoring, 3 cells (commits `9f57202`, `20f3510`, `6f4c635`) 💸 **API**
- **Script:** `run_secondary_scoring.py --cell {haiku_plain,gemini_plain,gpt_ignore}`
- **Outputs:** `data/scoring/secondary_*/` (each FROZEN with manifest + summary)
- **Deviation D1:** the first Gemini run aborted on a free tier quota
  misconfiguration. It is preserved unmodified at
  `data/scoring/secondary_gemini_plain_ABORTED_20260825/` as an audit
  trail (see `docs/deviations.md`). Never delete it.
- **Verification:** `verify_information_barrier.py --store <cell>`
  (✅ LOCAL) re-renders every prompt from the frozen template and essay
  text, checks the stored `prompt_sha256`, and confirms that no
  demographic field entered any prompt.

### 10. Secondary analyses + Holm family (commits `82effef`…`6f4c635`)
- **Scripts:** `stage_e_secondary.py`, `holm_secondary_family.py`, ✅ LOCAL
- **Outputs:** `results/secondary_*_analysis.json`,
  `results/secondary_confirmatory_{summary.json,family.md}`
- **Status:** PREREGISTERED SECONDARY (Holm, m = 3, α = 0.05). All three
  cells reject at adjusted p = 0.003.

### 11. Technical exclusion audit (commit `82effef`, post hoc, labeled)
- **Script:** `posthoc_exclusion_audit.py`, ✅ LOCAL
- **Outputs:** `results/posthoc_exclusion_audit.{md,json}`. Exclusions
  track essay length and congestion rather than ELL, and adversarial
  bounds cannot flip the primary direction.

### 12. Post hoc robustness package (commits `c17cb75`…`7174587`, plan frozen before execution)
- **Plan:** `docs/posthoc_robustness_plan.md`, committed and pushed
  BEFORE execution (`c17cb75`)
- **Scripts (in order):** `posthoc_quality_index.py`, `posthoc_feasibility.py`,
  `posthoc_robustness_tests.py`, `posthoc_validity.py`, `posthoc_paired.py`, all ✅ LOCAL
- **Outputs:** `results/posthoc/` (`robustness_tests.json`,
  `validity_alignment.json`, `paired_plain_vs_ignore.json`,
  `reviewer_tables.md`). The quality index and bins are hash frozen
  before any join with ELL or evaluator data.
- **Deviation D2** (the deduplication key correction, made before any
  join) is in `docs/deviations.md`.
- **Environment note:** these scripts ran under the system Python with
  pandas (see `docs/ENVIRONMENT.md`).

### 13. Evidence hierarchy (`docs/junior_spotlight_evidence.md`)
Separates preregistered confirmatory evidence, post hoc robustness
evidence, and interpretation limits for the paper.

## Raw evaluator stores: what a record contains

Each line of a `scores__<model>__<condition>.jsonl` is one API call:
`essay_id_comp`, `judge`, `condition`, `prompt_sha256` (hash of the exact
rendered prompt, used for the information barrier check), `raw_response`
(the verbatim provider response, e.g. `{"score": 4}`), `parsed_score`,
`parse_error`, `error_status`, `retry_count`, `prompt_tokens`,
`completion_tokens` (+ `thinking_tokens` for Gemini), `provider_model`,
`provider_request_id`, `request_id` (internal), `temperature_omitted`,
`timestamp_utc`. Provider request IDs and timestamps are retained as
provenance, since they let a provider confirm the calls happened as
described. They disclose nothing about writers. No essay text,
demographics, or human scores ever appear in these stores.

## Verifying the frozen record

```bash
python - <<'PY'
import hashlib, json, pathlib
for d in ['data/scoring/primary','data/scoring/secondary_haiku_plain',
          'data/scoring/secondary_gemini_plain','data/scoring/secondary_gpt_ignore',
          'data/scoring/secondary_gemini_plain_ABORTED_20260825']:
    man = json.loads(pathlib.Path(d,'FROZEN.json').read_text())
    for name, dig in man['files'].items():
        actual = hashlib.sha256(pathlib.Path(d,name).read_bytes()).hexdigest()
        print('OK ' if actual==dig else 'MISMATCH ', d+'/'+name)
PY
```
