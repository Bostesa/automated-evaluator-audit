# Civil Comments LLM-Evaluator Extension — Frozen Addendum

Frozen: 2026-08-27, before any Civil Comments evaluator score (Detoxify or
LLM) has been analyzed with respect to the identity attributes A, and before
any Civil Comments LLM API call. Machine-readable freeze:
`config/civil_comments_llm_evaluator_addendum.json`.

## Provenance and status language

- **PERSUADE** is the original preregistered/confirmatory case study, per its
  existing provenance (`config/preregistered.json`). This addendum does not
  modify it.
- **Civil Comments / Detoxify** is an additional audit whose specification was
  separately frozen at commit `861804b25f1afd8c81eb26d3e5bb35e2d4bec5a6`; its
  A-blind Detoxify score store, decile boundaries, and discrete score store
  were frozen at commit `510ece882ff119bdd459b8ab3df7a51353a2d67c`. Its
  eight-test confirmatory family (Holm across eight) is unchanged.
- **This LLM extension** is added and frozen BEFORE any Civil Comments
  evaluator score is joined to A or Z. Its 24 tests are a SECONDARY
  cross-evaluator replication family. It is not part of the original PERSUADE
  preregistration and not part of the original Civil Comments primary
  confirmatory family, and must never be described as either.

## Purpose

Evaluate the same frozen Civil Comments hypothesis — S independent of A given
Z — with both the already frozen conventional evaluator (Detoxify-original)
and a family of three LLM evaluators, so that any residual conditional
dependence can be checked for architecture-specificity.

## Evaluator family (exact frozen PERSUADE model IDs, reused verbatim)

| Evaluator | Provider | Exact model ID |
|---|---|---|
| GPT | OpenAI | `gpt-5.4-mini-2026-03-17` |
| Claude | Anthropic | `claude-haiku-4-5-20251001` |
| Gemini | Google | `gemini-3.7-flash` |

No substitution is permitted. If an exact model is not callable at scoring
time, scoring STOPS for a documented, publicly committed amendment; no other
model may silently take its place.

## Sample and information barrier

- LLM inference scores ONLY the frozen one-comment-per-article primary
  manifest (`results/civil_comments/primary_manifest.csv`, SHA-256
  `892245a7899401c1041f3cf7bc17528d80d9812efacefe994dbfd16fec97469e`,
  N = 69,573). The 448,000-comment census is NOT scored by the LLMs.
- The scoring stage may access only the stable comment id (request routing)
  and the raw comment text. It never receives identity attributes, human
  toxicity annotations, article metadata, A, Z, or any Detoxify score.
- Credential smoke tests use fixed non-dataset sentences only.

## Frozen rubric

One provider-neutral STANDARD toxicity rubric
(`prompts/civil_comments_toxicity_rubric.txt`, template SHA-256
`f4ca41197eb4c8c50177a55aeade783b804494a2d833d5c6ecb2bbd5f070077c`), a 1–5
integer scale returned as strict JSON `{"score": n}` with no explanation and
no chain of thought. The placeholder `[[COMMENT_TEXT]]` is replaced by the
raw stored comment text; the rendered prompt is byte-identical across
providers, whose only divergence is structured-output syntax. The rubric
deliberately contains NO instruction about identity, demographics, protected
characteristics, bias, or fairness: it is the standard prompt, not a
mitigation prompt. No prompt variants may be scored.

## Inference settings (frozen PERSUADE policy, reused)

Adapters: `offcriterion.pipeline.cc_toxicity_judges` (thin subclasses of the
frozen PERSUADE adapters; only the output schema changes to 1–5).

- Temperature 0 everywhere (OpenAI keeps the frozen omit-once-if-rejected
  fallback, recorded); seed 427183 where the API offers one (OpenAI, Gemini;
  Anthropic offers none — recorded); OpenAI `reasoning_effort: none`;
  Anthropic extended thinking off; Gemini `thinkingLevel: "low"` (the frozen
  PERSUADE-approved minimum) with billed thinking tokens recorded.
- Output caps: 100 tokens (OpenAI/Anthropic), 1000 (Gemini, thinking billed
  against the cap). Timeout 120 s.
- Retry: up to 3 retries of the identical request on 429/5xx/network errors
  with exponential backoff; any other 4xx aborts the run for report.
- A comment still failing after the retry policy is a technical exclusion,
  logged by id, never re-scored. A response that does not parse as a JSON
  object with the single key `score` and an integer 1..5 is an exclusion,
  never repaired or reprompted. No other exclusion exists. No item is ever
  selectively re-scored because its score looks unusual.
- Requests in ascending integer comment-id order; 10 worker threads per
  provider; append-only `RawScoreStore` per provider under
  `data/scoring/cc_<provider>_toxicity`; the store is SHA-256-frozen before
  that provider's scores may be joined to A/Z. Until then only pooled
  A-blind quantities (score distribution, failure counts, cost) may be
  inspected.

## Analysis (identical frozen machinery)

For every LLM evaluator: the frozen eight-identity A family and >= 1/2
exact-rational threshold; the exact seven-label Z vector; the frozen
`ConditionalG2` statistic; within-exact-Z permutation of A; B = 999;
p = (1 + #{T_b >= T_obs}) / 1000. S is the integer 1–5 rating used directly
(5 categories, no discretization). The descriptive companion is the
stratum-size-weighted conditional mean gap (A=1 minus A=0) on the 1–5 scale,
same weighting rule as the frozen Detoxify analysis. Per-evaluator analyses
run on that evaluator's validly scored subset; exclusions are reported,
never imputed.

Seeds: `SeedSequence(entropy=20260827, spawn_key=(slot, identity_index))`,
slots 11–13 (primary exact-Z, GPT/Claude/Gemini), 14–16 (binned-Z
sensitivity), 17–19 (negative control). Slots 1–5 and 9 remain the frozen
Detoxify analysis and are not reused.

## Multiplicity

- Detoxify: UNCHANGED — 8 tests, Holm across 8.
- LLM extension: ONE secondary replication family of 24 tests
  (3 evaluators × 8 identities), Holm across ALL 24 raw permutation
  p-values, alpha 0.05. No provider- or identity-level subfamily may be
  formed after results are seen.

## Robustness (compact, prespecified)

Per evaluator, exactly: (1) the primary exact-Z analysis; (2) the already
frozen semantic binned-Z sensitivity; (3) the already frozen negative-control
labels. NOT run: full-census LLM scoring/analysis, additional identities,
prompts, mitigation variants, or models; no LLM high-confidence-A variant.

## Technical-exclusion audit

After all three stores are frozen: join per-comment technical/invalid status
(not scores) to A and comment length; report overall and per-identity
exclusion rates, two-sided Fisher exact association tests, and whether
missingness threatens interpretation. This audits missingness; it never
modifies the frozen exclusion rules.

## Cost / availability check

Before the first dataset API call: compute the exact number of comments,
estimate token volume from A-blind text lengths, estimate per-provider cost
from the frozen PERSUADE pricing records, log the estimate, and verify
credentials and exact-model availability with non-dataset smoke calls. The
estimate is informational and never changes the frozen evaluator family.

## Interpretation limits

A rejection means only that the evaluator score retains residual conditional
statistical dependence on an identity-mention attribute among comments with
identical observed human toxicity annotation vectors. It does not establish
discrimination, unfairness, causal use of identity, demographic inference,
intent, that identity language is inherently irrelevant to toxicity, or that
human annotations measure toxicity perfectly. Cross-evaluator claims may be
made only if the frozen results support them; Detoxify/LLM disagreements are
reported as disagreements.
