# Civil Comments Gemini Missing-Score Bound — Frozen Pre-Analysis Specification

Frozen: 2026-08-29, BEFORE any bound value has been computed. This is the LAST
authorized experimental/statistical analysis for the project. It uses frozen
data only — no APIs, no rescoring, no alteration of any frozen primary or
augmented-Z result. Machine-readable freeze:
`config/civil_comments_gemini_missing_bound_spec.json`.

## Status

- **Descriptive missing-outcome sensitivity analysis** for the primary Civil
  Comments Gemini conditional mean gap. It is NOT confirmatory, does NOT alter
  the primary ConditionalG2 tests, creates NO new p-values, and forms NO new
  multiplicity family.
- Run for ALL EIGHT Gemini identities, not a subset selected on significance
  status, to avoid outcome-dependent selection.

## Pinned frozen inputs

- Primary manifest: `results/civil_comments/primary_manifest.csv`, SHA-256
  `892245a7899401c1041f3cf7bc17528d80d9812efacefe994dbfd16fec97469e`,
  N = 69,573.
- Frozen Gemini score store:
  `data/scoring/cc_gemini_toxicity/scores__gemini-3.7-flash__cc_toxicity.jsonl`,
  SHA-256
  `3ef469677c9ae7f0a89924af3476fc0b92c352376b464d8b888efa454a4f58f1`
  (matches `results/civil_comments/llm_scores_gemini_FROZEN.json`):
  67,183 valid, 2,384 technical exclusions, 6 invalid responses
  (2,390 missing total, 3.44%).
- Identity definitions (eight, unchanged): `A = 1` iff the stored identity
  column value is `>= 1/2` exactly (`attribute_value`), for
  black, white, LGBTQ, muslim, christian, other_religions, male, female.
- Conditioning set: the frozen primary exact seven-label human-annotation
  vector `Z` (`z_key_exact`), unchanged.
- Gap definition: the project's existing weighted conditional-gap
  (`weighted_mean_gap`) — stratum-size-weighted `mean(S|A=1) - mean(S|A=0)`
  over informative (mixed-A) strata, on the 1–5 scale, unchanged.

## Bound definition

The "missing rows" are the 2,390 frozen Gemini rows with a technical exclusion
(`error_status`) or an invalid response (`parsed_score` null). Their comment
ids, A, and Z are known; only their score is missing.

For each identity, the observed primary Gemini gap `Delta` is the frozen
weighted conditional-gap over the 67,183 validly-scored rows (the analysis
recomputes it and asserts equality to the frozen primary Gemini gap).

Worst-case bounds supply bounded scores to the 2,390 missing rows within the
frozen evaluator scale [1,5] and recompute the weighted conditional-gap on the
resulting complete data, using the intended primary support (informative
primary-Z strata) after the bounded scores are supplied:

- **Lower bound:** every missing row with `A=1` receives score **1**; every
  missing row with `A=0` receives score **5**.
- **Upper bound:** every missing row with `A=1` receives score **5**; every
  missing row with `A=0` receives score **1**.

Validly-scored rows keep their real frozen scores. This per-stratum assignment
minimises (lower) / maximises (upper) each stratum's `mean(S|A=1)-mean(S|A=0)`;
because stratum weights depend only on (A, Z) and are unchanged by the imputed
values, the recomputed weighted gap is the exact worst-case bound.

Prohibited: assuming missing-at-random; altering Z; altering A; changing the
weighting; optimising a different support definition; generating permutation
p-values from the imputed data.

## Report (eight identities)

Per identity: observed primary Gemini gap; total missing; missing A=1; missing
A=0; worst-case lower-bound gap; worst-case upper-bound gap; whether zero lies
in the interval; whether the positive sign is guaranteed under arbitrary
missing-score assignment (i.e. lower bound > 0). Also: narrowest interval;
widest interval; identities whose sign is identified; identities whose sign is
not identified.

## Precommitted interpretation

- If lower bound > 0: "Even adversarial assignment of all missing Gemini scores
  within the 1–5 range cannot reverse the positive conditional mean gap."
- If the interval contains 0: "The sign of the Gemini conditional mean gap is
  not identified without assumptions about the missing scores."
- For `christian` specifically (its exclusion rate is already known to be
  associated with A): if its interval contains zero, describe the
  Gemini-`christian` estimate as especially uncertain.
- Do NOT infer anything about G^2 significance from these mean-gap bounds.
- No causal, discrimination, or fairness language.

## Execution order

Commit and push this document, the config, and the analysis script
`scripts/civil_comments_gemini_missing_bound.py` as the pre-analysis freeze;
verify `origin/main`; report the pre-analysis commit SHA. Only then compute the
eight-row bound; freeze/SHA-256-hash the result
(`results/civil_comments/gemini_missing_bound.json`); verify all eight rows;
commit and push. Then STOP — the empirical phase is permanently closed.
