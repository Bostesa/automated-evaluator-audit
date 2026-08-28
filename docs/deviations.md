# Post-preregistration deviations

Per §20 of [`preregistration.md`](preregistration.md), every departure from
the frozen protocol after any judge output was observed is reported here
with its trigger and its consequence for interpretation.

## D1 — Gemini confirmatory cell restarted after quota misconfiguration (2026-08-25)

**Classification:** post-preregistration **technical** deviation. Decided by
the investigator **before any Gemini hypothesis analysis or result
inspection** (the aborted store was never joined to attributes and never
entered any analysis path).

**Trigger:** provider quota configuration. The first execution of the
`gemini-3.7-flash` (plain) secondary confirmatory cell ran against a Google
Cloud project on the **Gemini API free tier — 5 requests/minute** for this
model. Under that quota the frozen retry policy (up to 3 retries with
seconds-scale exponential backoff) fails essentially every call: 86 of the
first 87 census records became HTTP-429 technical exclusions before the run
was stopped, which would have destroyed the cell mechanically rather than
measured anything about the judge.

**Action:**

1. The 87-record first store was **preserved unmodified as an audit trail**
   at `data/scoring/secondary_gemini_plain_ABORTED_20260825/`, checksum-
   frozen (raw-file SHA-256
   `2a9b0ee2943b0ba44480a938fd521fac3072557d0341d4ef4b784ee252caf01f`) and
   marked `ABORTED_QUOTA_MISCONFIGURATION`. **No scientific analysis is or
   will be performed on it** (it contains 1 valid score and 86 quota
   failures).
2. After billing was enabled and paid-tier quota verified with the same
   degenerate-strata smoke procedure used for every judge, the cell was
   **restarted from the full frozen 11,360-essay census** in a fresh
   append-only store (`data/scoring/secondary_gemini_plain/`).
3. **Nothing scientific changed:** same frozen prompt template, same pinned
   model ID, same approved low-thinking setting, same 3-retry/exclusion
   policy, same census manifest, same strata, statistic, permutation seeds,
   and analysis path.

**Consequence for interpretation:** the deviation is purely operational
(which API calls were billed against which Google quota tier). Because the
restart decision was made on quota-error evidence alone — no Gemini score
distribution, no attribute join, no test statistic existed — it cannot have
been influenced by any result, and the Gemini cell's confirmatory status
under the preregistered Holm family is retained, with this deviation
reported alongside it. The one valid score in the aborted store was
discarded with the store (not merged), keeping the analysed Gemini scores a
single-provenance, single-quota-regime run.

## Operational notes (non-deviations)

- **Gemini daily-cap interruption (2026-08-25).** The restarted Gemini run
  hit the paid tier's `generate_requests_per_model_per_day` limit (10,000)
  after 9,981 valid scores; 743 calls failed as HTTP-429 after the frozen
  3-retry policy and are **final technical exclusions under preregistered
  exclusion rule 2** — the same rule that produced the primary's 467. The
  run was then resumed for the 636 essays with no record, using an API key
  from a second paid-tier Google project. Key rotation is purely
  operational: endpoint, pinned model ID, request parameters, prompt, and
  policy are identical, and keys never enter the scored records. No
  excluded or scored essay was ever re-called.
- **Post-exclusion thresholds:** all cells satisfy the preregistered
  minimums (analysed ELL >= 900, informative strata >= 28): primary 1,000 /
  31; Haiku 1,039 / 31; Gemini 958 / 31; GPT-ignore 977 / 31.

## D2 — post-hoc plan implementation correction (dedup key), 2026-08-25

The frozen post-hoc plan (section 2.1) specified dropping exact duplicate
`(essay_id_comp, discourse_id)` rows as a no-op safeguard ("none expected").
On first execution this dropped 124,338 rows: `discourse_id` turns out to be
Excel-mangled scientific notation (728 distinct values across 173,266 train
rows), the same corruption `data/persuade/README.md` documents for
`essay_id`. The safeguard key was corrected to
`(essay_id_comp, discourse_start, discourse_end)`, which was verified to
contain zero duplicates (and train/test essay sets are disjoint), so the
corrected safeguard is the intended no-op. The correction was made before
any join with ELL status or judge scores and before any feasibility or
robustness statistic was computed; the resulting index matches the schema
check recorded in the plan (100% coverage, median 9 elements/essay).

## D3 — Civil Comments Gemini quota-recovery execution history and frozen terminal rule (2026-08-28)

The Civil Comments Gemini scoring branch (secondary LLM-evaluator extension,
`docs/civil_comments_llm_evaluator_addendum.md`) repeatedly hit per-project
daily request quotas. The frozen scientific specification (model ID, prompt,
schema, settings, 3-retry/exclusion policy, manifest, ordering, append-only
store) never changed. The operational monitoring around it was refined
during execution — original >50 failure guard, segment-2 guard threshold
error, proactive watchdog, stale-log false trigger, burst-verified 15-call
prober, store-level 10-failure watchdog — each on quota/log evidence alone.
These refinements are **technical execution history**, not part of the
frozen specification; they are itemized in
`docs/civil_comments_gemini_terminal_rule.md` and
`results/civil_comments/gemini_credential_provenance.json`.

On 2026-08-28T04:41Z — before any Civil Comments LLM S-versus-A result had
been computed or inspected — a final outcome-blind terminal execution rule
was frozen for this branch (`docs/civil_comments_gemini_terminal_rule.md`,
machine-readable `config/civil_comments_gemini_terminal_rule.json`): a hard
logistics-based wall-clock cutoff of **2026-08-31T07:00:00Z**, permanent
preservation of all successes and frozen exclusions, no rescoring of frozen
technical exclusions, scoring of genuinely unresolved rows only, and a
prescribed incomplete-at-cutoff procedure (stop, preserve the partial store,
report coverage as a provider-level incomplete-scoring deviation, and leave
any consequence for the prespecified 24-test family to a user decision made
with the deviation visible — never a silent redefinition).
