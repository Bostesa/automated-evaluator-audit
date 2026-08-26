# Secondary confirmatory family — results

Preregistered family of exactly three tests (Holm, m = 3, familywise
α = 0.05; `docs/preregistration.md` §11). The primary test was
preregistered separately as the single primary test and is **not** a member
of this family; its row appears for comparison only. Machine-readable
detail: [`secondary_confirmatory_summary.json`](secondary_confirmatory_summary.json);
per-cell reports `secondary_*_analysis.json`; frozen stores and hashes in
`data/scoring/secondary_*/stage_d_summary.json`. Post-preregistration
deviation D1 and operational notes: [`../docs/deviations.md`](../docs/deviations.md).

All cells: frozen census manifest (11,360 essays), native 1–6 score space,
exact (prompt, human score) strata, conditional G², B = 999 within-stratum
permutations with frozen seed slots, frozen 3-retry/exclusion policy,
information barrier verified in code per store (all 11,360 stored prompt
hashes match the frozen-template + essay rendering; stores checksum-frozen
before any attribute join).

## Comparison table

| Judge / condition | N | ELL N | Strata | Cond. G² | raw p | Holm p | Reject | Cond. mean diff | P(S≥4) shift | Tech. excl. | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **PRIMARY: GPT-5.4-mini, plain** | 10,893 | 1,000 | 31 | 420.86 | 0.001 | — (primary) | reject (α=0.05) | −0.320 | −0.243 | 467 | $12.34 |
| Claude Haiku 4.5, plain | 11,360 | 1,039 | 31 | 691.58 | 0.001 | 0.003 | reject | −0.598 | −0.344 | 0 | $19.28 |
| Gemini 3.7 Flash, plain | 10,617 | 958 | 31 | 500.95 | 0.001 | 0.003 | reject | −0.444 | −0.215 | 743 | $18.27 |
| GPT-5.4-mini, ignore-demographics | 10,797 | 977 | 31 | 459.08 | 0.001 | 0.003 | reject | −0.362 | −0.261 | 563 | $12.60 |

Same-draw companion statistics (all p = 0.001 in every cell): stratified
mean disparity 0.321 / 0.599 / 0.452 / 0.363; stratified regression LRT
405.62 / 765.38 / 497.87 / 431.77. Raw p = 0.001 is the minimum attainable
at B = 999; Holm-adjusted 0.003 = 3 × 0.001 for all three (step-down with
tied minima).

Ordinal shift profiles (cumulative P(S≥k | ELL) − P(S≥k | non-ELL),
stratum-weighted):

| k | Primary | Haiku | Gemini | GPT-ignore |
|---|---|---|---|---|
| ≥2 | −0.000 | −0.001 | −0.000 | −0.001 |
| ≥3 | −0.015 | −0.230 | −0.135 | −0.009 |
| ≥4 | −0.243 | −0.344 | −0.215 | −0.261 |
| ≥5 | −0.063 | −0.024 | −0.090 | −0.092 |
| ≥6 | 0.000 | 0.000 | −0.004 | 0.000 |

Token usage: Haiku 18.77M in / 0.10M out; Gemini 15.04M in / 0.08M out plus
**1.78M billed thinking tokens** (approved low-thinking setting, recorded
separately, billed as output); GPT-ignore 15.93M in / 0.14M out. Secondary
program cost: **$50.15** (frozen preregistration estimate: $43–48 plus
Gemini thinking-token uncertainty).

## Conservative reading of the preregistered questions

1. **Replication across model families:** yes. All three secondary tests
   reject after Holm at familywise α = 0.05. Residual conditional
   dependence of judge score on ELL status given (human score, prompt) is
   present for judges from all three providers.
2. **Effect of the ignore-demographics instruction:** no material
   reduction. −0.362 vs the primary's −0.320 (same judge, same essays);
   the dependence is, if anything, nominally slightly larger. This does
   **not** establish that the judge deliberately uses demographic
   reasoning — only that the frozen instruction did not remove the
   ELL-correlated signal.
3. **Direction:** consistent. Every judge scores ELL essays lower on
   average conditional on human score and prompt (−0.32 to −0.60 rubric
   points).
4. **Form of dependence:** judge-specific. The primary and the
   ignore-demographics condition concentrate the shift almost entirely at
   the 3-vs-4 boundary. Gemini spreads it across the 2→3, 3→4 and 4→5
   boundaries; Haiku shows a broad two-boundary shift (≥3 and ≥4). The
   "single 3-vs-4 location shift" description is specific to the
   GPT-5.4-mini judge, not universal.

Interpretation boundaries of §18 apply unchanged: rejection is evidence of
residual conditional dependence, not of causal use of ELL status, not of
discrimination, and not a claim that the human score is ground truth.
Technical-exclusion selection is characterized in the post-hoc audit
(`posthoc_exclusion_audit.md`): exclusions track essay length and request
congestion, not ELL, and no admissible configuration of the primary's
excluded scores could eliminate the observed deficit.

**The confirmatory program ends here.** Gender, race, economic status,
disability, per-prompt tests, source-based prompts, alternative
conditioning, transformations, or statistics remain exploratory and
require a separate decision.
