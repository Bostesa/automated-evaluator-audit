# Civil Comments Augmented-Z Robustness — Frozen Pre-Analysis Specification

Frozen: 2026-08-29, BEFORE any augmented-Z evaluator result has been computed.
The GPT, Claude, and Gemini score stores are frozen and the primary 24-test
family is complete (commit `cc6d9dd`); no augmented-Z ConditionalG2 statistic,
gap, or decomposition quantity has been computed. Machine-readable freeze:
`config/civil_comments_augmented_z_spec.json`.

## Status and provenance

- This is a **secondary robustness analysis** for the Civil Comments LLM
  extension (`docs/civil_comments_llm_evaluator_addendum.md`). It is NOT part
  of the PERSUADE preregistration, NOT the Civil Comments primary confirmatory
  family, and NOT the frozen 24-cell secondary replication family. It must
  never be described as any of those.
- It adds one robustness question — does the residual conditional dependence
  survive adding a comment-length stratum to the human-annotation conditioning
  set — plus a **descriptive** common-support decomposition of any gap change.
- No further specification changes are authorized after the commit that freezes
  this document.

## Augmented-Z definition

Let `Z_primary` be the frozen exact seven-label human-annotation vector
(`z_key_exact`: exact reduced rationals of `toxicity, severe_toxicity,
identity_attack, insult, threat, obscene, sexual_explicit`, frozen order).

Define a **binary comment-length stratum** `L`, deterministic and A-blind:

- `length(row) = len(row["comment_text"])` (character count of the raw stored
  comment text, the same length measure used by the frozen missingness audit);
- `M` = the median character length over the frozen primary manifest's 69,573
  comments, computed once, A-blind and evaluator-independent. **M = 225**
  (verified from the frozen manifest; the analysis recomputes M and asserts it
  equals 225);
- `L = 1` iff `length > M`, else `L = 0` (ties at exactly M map to 0). Under
  this rule L=1 covers 34,712 comments and L=0 covers 34,861.

The **augmented-Z stratum key** is `Z_aug = (Z_primary, L)` —
`z_key_augmented(row) = z_key_exact(row) + "|L=" + str(L)`. L depends only on
comment text length; it never uses A, Z human labels, evaluator scores, or
identity attributes.

## Inferential augmented-Z result (unchanged machinery)

For each of the 24 evaluator × identity cells (3 evaluators × 8 frozen
identities), on the evaluator's already-frozen validly-scored subset:

- statistic: `ConditionalG2` over the full 1–5 score distribution;
- within-exact-`Z_aug` permutation of A; B = 999; permutation p-value
  `p = (1 + #{T_b >= T_obs}) / (B+1)`;
- seeds: `SeedSequence(entropy=20260827, spawn_key=(slot, identity_index))`,
  new slots **20/21/22** for gpt/claude/gemini (disjoint from the primary
  11–13, binned 14–16, negative-control 17–19);
- multiplicity: **Holm across all 24 augmented-Z raw permutation p-values**,
  alpha 0.05. This is a robustness family separate from the primary 24; no
  provider- or identity-level subfamily may be formed after results are seen.

A stratum is informative iff it contains both A=0 and A=1 rows (size >= 2,
mixed A); single-A / degenerate strata contribute nothing to the within-stratum
permutation and are dropped, exactly as in the primary analysis. Because
splitting a primary-Z stratum by L can turn a previously mixed-A stratum into
single-A sub-strata, the augmented-Z analysis may retain fewer rows than the
primary analysis for a given cell.

## Descriptive common-support decomposition (descriptive only)

For every evaluator × identity cell, define three gaps (each the frozen
stratum-size-weighted conditional mean difference `mean(S|A=1) - mean(S|A=0)`
over informative strata, `weighted_mean_gap`, on the 1–5 scale):

- **primary_gap** = the already-frozen primary-Z conditional mean gap on the
  original primary-analysis retained rows (taken from
  `results/civil_comments/llm_audit_results.json`,
  `llm_secondary_replication_family.tests[cell].weighted_mean_gap_1to5`; the
  analysis recomputes it and asserts equality to the frozen value).
- **augmented_gap** = the augmented-Z conditional mean gap on the rows retained
  by the augmented-Z analysis (informative `Z_aug` strata).
- **primary_common_support_gap** = the conditional mean gap using **primary Z
  only**, computed on **exactly** the observation rows that enter that cell's
  augmented-Z analysis.

The common-support row set for a cell is the exact final analyzable row set
used for augmented-Z, obtained after (a) applying the evaluator's already-frozen
valid/missing status and (b) applying the identity-specific augmented-Z mixed-A
support rule (rows in informative `Z_aug` strata). It is not chosen any other
way: no different common-support set, no restoration of rows augmented-Z
dropped, and never any use of evaluator score VALUES to choose common support.

Quantities per cell:

```
composition_change  = primary_common_support_gap - primary_gap
conditioning_change = augmented_gap - primary_common_support_gap
total_change        = augmented_gap - primary_gap
composition_abs_change  = abs(composition_change)
conditioning_abs_change = abs(conditioning_change)
```

The additive identity `total_change = composition_change + conditioning_change`
holds by construction and is **verified numerically for all 24 cells** to
floating-point tolerance (1e-9).

No p-values, permutation tests, confidence intervals, or new multiplicity
family are attached to `primary_common_support_gap` or to any decomposition
quantity. The decomposition is **descriptive only**. The inferential
augmented-Z robustness result remains the ConditionalG2 permutation test with
Holm across the 24 augmented-Z cells, above.

If a cell has no informative `Z_aug` stratum (empty augmented common support),
its augmented_gap and primary_common_support_gap are reported as null, the
identity check is skipped for that cell, and the cell is flagged; augmented-Z
never imputes.

## Interpretation commitment (precommitted)

- If the primary → primary_common_support step accounts for most of a gap
  change (|composition_change| dominates), describe the change as primarily due
  to the **altered retained support / composition**, not as evidence that
  length conditioning explains the association.
- If the primary_common_support → augmented step dominates
  (|conditioning_change| dominates), describe the change as primarily
  **associated with additional conditioning on length**.
- If both components contribute materially, report both.
- If the augmented gap increases, use the same decomposition to distinguish
  composition-driven amplification from conditioning-driven amplification.
- No causal language ("length causes", "length mediates"). The strongest
  permitted wording is that additional conditioning on length **changes,
  attenuates, or amplifies** the residual association on the common support.

## Prediction (unchanged; not redefined by the decomposition)

> Adding a binary comment-length stratum to the exact seven-label human
> annotation vector will leave the Civil Comments LLM conditional gaps largely
> intact. Among cells with primary |Δ| >= 0.05, we predict the median absolute
> relative change in Δ will be below 15%. Absolute gap changes will be reported
> for all 24 cells regardless of primary effect size.

Relative change in Δ is `total_change / primary_gap`; the prediction is
evaluated on the median absolute relative change among cells with primary
|Δ| >= 0.05, on the total change. The common-support decomposition diagnoses
WHY any observed total change occurred; it is not used to redefine whether the
prediction passed.

## Report contents

Per-cell (all 24 rows): evaluator, identity; the already-specified support
columns (`n_total`, `n_a1_total`, `n_informative_strata`,
`n_retained_informative`, `n_retained_a1` under augmented-Z) and the primary
retained counts; the augmented-Z `observed_conditional_g2`, `p_raw`, `p_holm`,
`reject_holm_at_0.05`; the already-specified relative-change column
(`total_change / primary_gap`); and the new decomposition columns:

- primary_gap
- primary_common_support_gap (primary-on-augmented-common-support gap)
- augmented_gap (augmented-Z gap)
- composition_change
- conditioning_change
- total_change
- composition_abs_change
- conditioning_abs_change

Summary: prediction evaluation (median absolute relative change among primary
|Δ| >= 0.05 cells vs the 15% threshold; per-cell absolute changes for all 24);
median absolute composition change across 24; median absolute conditioning
change across 24; cell with the largest absolute composition change; cell with
the largest absolute conditioning change; and, for the cell with the largest
absolute total change, the full decomposition. The additive identity is
verified for all 24 cells.

## Freeze / execution order

1. This document and `config/civil_comments_augmented_z_spec.json`, together
   with the analysis script `scripts/civil_comments_augmented_z.py`, are
   committed and pushed as the PRE-ANALYSIS specification. No result is
   computed before that commit.
2. Only then is the augmented-Z analysis run, producing
   `results/civil_comments/augmented_z_results.json`, which is frozen/hashed
   and committed.
3. Execution STOPS there — no manuscript editing and no Gemini missingness
   bound in this task.

Frozen inputs the analysis verifies before reading: the primary manifest SHA,
the negative-control labels SHA (via the shared machinery), each evaluator's
frozen score-store SHA-256, and the frozen primary gap for each cell.
