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
