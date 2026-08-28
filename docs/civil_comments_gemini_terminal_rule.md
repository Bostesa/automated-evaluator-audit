# Civil Comments Gemini Terminal Execution Rule — Frozen

> **AMENDED 2026-08-28:** the hard wall-clock cutoff
> 2026-08-31T07:00:00Z below is SUPERSEDED by
> `docs/civil_comments_gemini_terminal_rule_amendment1.md`
> (prospective, infrastructure-only; made before any LLM S-versus-A
> result existed). Every other provision remains in force. The
> original text is preserved unchanged below.

Frozen: 2026-08-28T04:41Z, BEFORE any Civil Comments LLM S-versus-A result
(GPT, Claude, or Gemini) has been computed or inspected. The GPT and Claude
stores are frozen but unanalyzed; the Gemini store is partial and unanalyzed;
no LLM score has been joined to A or Z. Machine-readable freeze:
`config/civil_comments_gemini_terminal_rule.json`.

Purpose: fix ONE final outcome-blind execution rule for the Gemini scoring
branch so that quota recovery cannot become an indefinite infrastructure
chase, and so that no completion/stopping decision can ever be influenced by
a scientific result.

## Terminal rule

1. **Credential rotation** continues exactly under the already documented
   policy in `results/civil_comments/gemini_credential_provenance.json`
   (rotation as infrastructure failover only; frozen order gemini_primary,
   gemini_backup1, gemini_backup2; identical model/prompt/settings across
   credentials; successful rows never rescored).
2. **Preserved permanently:** every successful Gemini score, every frozen
   invalid-response exclusion, and every quota-period technical exclusion
   already written under the frozen 3-retry policy.
3. **No rescoring of frozen technical exclusions.** The 2,339 currently
   frozen quota technical exclusions — and any future item that becomes a
   frozen technical exclusion under the same policy — are NEVER rescored.
   (Enforced structurally: the scorer's resume logic treats any recorded row,
   success or failure, as done.)
4. **Only genuinely unresolved manifest rows** (rows with no record of any
   kind in the append-only store) may be scored.
5. **Outcome blindness.** All quota probing, credential rotation, and
   watchdog decisions are functions ONLY of HTTP status codes, record counts,
   and non-dataset smoke calls. They remain completely blind to A, Z,
   Detoxify scores, GPT scores, Claude scores, and Gemini score values.
6. **Infrastructure refinements are execution history, not specification.**
   See "Technical execution history" below.

## Hard completion / stopping rule

**Cutoff: 2026-08-31T07:00:00Z (deterministic wall clock).**

Basis (fixed before any LLM S-versus-A result exists; logistics only):

- 44,462 manifest rows remain unresolved. Observed provider behavior is
  ~10,000 successful requests per project per day (watchdog-limited to
  ~9,700 per segment), across three authorized projects ≈ 29,100/day.
- The cutoff allows three further full daily quota windows (the Pacific-day
  windows of 2026-08-28, -29, -30), ≈ 87,000 capacity ≈ 2x the requirement:
  two clean windows suffice, one full window of contingency.
- Stopping no later than the morning of 2026-08-31 leaves the remaining
  schedule for: Gemini freeze, the 24-test analysis, binned-Z sensitivities
  and negative controls, verification, paper integration, and compiling and
  inspecting the two-page submission — all downstream steps that must not be
  compressed by an open-ended scoring chase.

The cutoff may not be chosen again or moved after any LLM S-versus-A result
is visible. At the cutoff:

- **A. Complete:** if all resolvable Gemini rows are done, freeze the store
  normally under the existing frozen plan.
- **B. Incomplete solely due to quota exhaustion of all authorized
  projects:** STOP Gemini inference. Preserve the partial store exactly.
  Record: valid N; invalid-response exclusions; quota technical exclusions;
  never-attempted/unresolved N; request-order ranges; credential/project
  segments; and the reason the branch stopped. Never-attempted rows are NOT
  converted into ordinary item-level technical exclusions. This is recorded
  as a provider-level incomplete-scoring deviation.
- **C.** The frozen manifest (N = 69,573) is never shrunk retrospectively.
- **D.** No substitute Gemini model.
- **E.** No new provider accounts/projects without explicit user
  authorization.

## If Gemini is incomplete at the cutoff

The frozen 24-test confirmatory family is NOT automatically redefined.
Instead: (1) GPT and Claude are frozen normally; (2) the partial Gemini
store and its missingness metadata are frozen; (3) BEFORE computing the
24-test family, execution STOPS and the exact Gemini coverage/deviation is
reported to the user; (4) the user decides how the prespecified family is
reported — the missing Gemini cells are never presented as prospectively
removed, and the multiplicity question is not resolved unilaterally after
results are visible.

## If Gemini completes

Proceed exactly per the existing frozen plan
(`docs/civil_comments_llm_evaluator_addendum.md`): freeze/hash the Gemini
store; missingness audits; all 24 LLM tests; Holm across all 24; negative
controls; binned-Z sensitivities; cross-evaluator summary; tests/checksums;
commits/pushes.

## Current-state ledger (verified from files, 2026-08-28T04:40Z)

Recomputed directly from
`data/scoring/cc_gemini_toxicity/scores__gemini-3.7-flash__cc_toxicity.jsonl`
(25,111 append-only records, 25,111 unique comment ids, zero duplicates) and
`results/civil_comments/primary_manifest.csv` (69,573 ids):

| Category | N |
|---|---|
| Valid scores | 22,769 |
| Invalid-response exclusions | 3 |
| Quota technical exclusions (frozen) | 2,339 |
| Unresolved (no record; still scoreable) | 44,462 |
| **Manifest total** | **69,573** |

Request-order ranges and per-credential segments are recorded in
`results/civil_comments/gemini_credential_provenance.json`.

## Technical execution history (deviations from planned monitoring; NOT part of the frozen scientific specification)

The frozen scientific specification is unchanged throughout: model ID,
prompt, schema, generation settings, 3-retry/exclusion policy, manifest,
ascending-id ordering, append-only store. The following operational
monitoring refinements were made during execution, each on quota/log
evidence alone, and are recorded as technical execution history:

1. **Original >50 failure guard** — the initial run-level guard stopped the
   scorer only after a large failure count (>50), allowing 559 quota-flood
   exclusions in segment 1 before the stop.
2. **Segment-2 guard issue** — a monitoring-threshold error allowed ~1,029
   flood exclusions in segment 2 before the manual stop.
3. **Proactive watchdog** — from segment 3, an external watchdog stopped the
   scorer at ~9,850 segment successes or >=25 segment failures to rotate
   before the daily-quota flood.
4. **Stale-log false trigger** — on 2026-08-27T18:05Z the watchdog fired on a
   stale log line; 18 valid rows were scored before the erroneous stop and
   the run was relaunched; all rows append-only, none rescored.
5. **Burst-verified prober** — after a single-call probe success proved to be
   a token-bucket trickle rather than a daily reset (segment 4: 7 successes,
   507 flood exclusions), the prober was hardened to require 15 consecutive
   clean non-dataset calls before any resumption.
6. **Store-level 10-failure watchdog** — the current watchdog polls the
   append-only store every 5 s and stops the scorer at >=10 new error
   records or >=9,700 new segment successes.

None of these refinements read, or could read, any score value, A, Z, or any
other provider's scores; they observed only HTTP error statuses, counts, and
timestamps.
