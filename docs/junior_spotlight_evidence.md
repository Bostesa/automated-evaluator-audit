# Junior Spotlight — evidence hierarchy

This document separates every result in the repository into exactly three
categories. Category A is the preregistered confirmatory evidence and is
closed. Categories B and C were produced or fixed after the confirmatory
results were known and may never be promoted to category A.

## A. Preregistered confirmatory evidence

1. **Synthetic validation, frozen before real scoring** (commit `6ba8331`,
   results in `results/results.md`): the stratified conditional-G²
   permutation audit holds its nominal size on null scenarios and detects
   variance-only (power 1.000 at n = 2000) and shape-only (0.705) departures
   that mean-based statistics miss entirely (~0.05), while matching them on
   location shifts. This is what licenses the omnibus method.
2. **Primary result** (`results/primary_analysis.json`): GPT-5.4-mini, plain
   rubric, PERSUADE 2.0 Independent-task census (N = 10,893 valid of the
   frozen 11,360; 1,000 ELL; 31 strata): conditional G² = 420.86, Monte Carlo
   p = 0.001 (B = 999, smallest attainable), weighted conditional ELL − non-ELL
   mean difference = −0.320. The preregistered null S ⫫ ELL | (prompt, human
   score) is rejected.
3. **Secondary confirmatory family, Holm-corrected (m = 3, α = .05)** — all
   reject at adjusted p = 0.003:
   - Claude Haiku 4.5, plain: G² = 691.58, Δ = −0.598 (N = 11,360).
   - Gemini 3.7 Flash, plain: G² = 500.95, Δ = −0.444 (N = 10,617).
   - GPT-5.4-mini, ignore-demographics: G² = 459.08, Δ = −0.362 (N = 10,797).
4. **Negative control** (`results/negative_control.json`): within-stratum
   random relabelling run through the identical path does not reject.
5. **Technical-exclusion audit** (`results/posthoc_exclusion_audit.md`) —
   explicitly **post-hoc diagnostic**, listed here only because it guards the
   primary claim: exclusions (4.11%, all HTTP-429) are predicted by essay
   length and request congestion, not ELL (OR 1.04, p = .85); the most
   adversarial admissible assignment of all 467 excluded scores cannot
   reverse the sign of the primary conditional mean difference.

Deviation D1 (Gemini free-tier abort and restart) and D2 (post-hoc dedup-key
correction) are recorded in `docs/deviations.md`.

## B. Post-hoc robustness evidence (frozen plan: `docs/posthoc_robustness_plan.md`, commit `c17cb75`)

All items below were run after the confirmatory results were known, under a
plan committed and pushed before execution. None are confirmatory.

1. **Richer human-quality adjustment (Z1)**: adding a within-stratum tertile
   of human discourse-effectiveness (Q; 100% essay coverage, Spearman
   ρ(Q, Y) = 0.57) to the conditioning set retains 99.0% of ELL essays across
   66 informative strata and attenuates |Δ| by only 3.1–4.2% across the three
   plain-rubric judges; all G² remain extreme (p = 0.001).
2. **Length-adjusted sensitivity (Z2)**: further adding a within-stratum
   median split of essay word count (97.5% ELL retention, 111 strata)
   attenuates |Δ| by 4.3% (GPT), 7.9% (Haiku), 10.9% (Gemini); all still
   p = 0.001. Residual judge-score dependence on ELL status is essentially
   unexplained by the richest available independent human quality signals.
3. **Paired plain vs ignore-demographics (GPT-5.4-mini)**
   (`results/posthoc/paired_plain_vs_ignore.json`): on 10,353 paired essays
   (942 ELL), Δ_plain = −0.314, Δ_ignore = −0.371; attenuation = −0.057,
   95% stratified-bootstrap interval [−0.093, −0.014], post-hoc permutation
   p = .022. Per the pre-fixed interpretation rule this is **evidence of
   (mild) worsening, not mitigation**: the instruction raised scores overall
   (+0.16) but raised non-ELL essays more than ELL essays.
4. **Judge-vs-human alignment** (`results/posthoc/validity_alignment.json`):
   on the 9,679-essay complete-case intersection, Spearman vs the human
   score 0.62 (Haiku), 0.64 (GPT), 0.78 (Gemini); QWK 0.56–0.74; within-1
   agreement 93–98%. Score compression is real, especially for GPT: 2.6
   effective categories, 92% of scores in {3, 4}, category 6 never awarded
   under the plain rubric. The judges are functioning, meaningfully
   rubric-tracking evaluators — and exhibit the residual ELL dependence
   while doing so.

## C. Interpretation limits

1. The human holistic score is not ground truth; it is a benchmark
   reference produced by human raters with their own biases.
2. The human discourse-effectiveness annotations are also imperfect proxies
   for the intended writing construct.
3. Residual conditional dependence does not establish causal use of ELL
   status by any judge.
4. Residual dependence does not establish discrimination or unfairness.
5. ELL-correlated linguistic features may be construct-relevant under a
   writing rubric; conditioning on Y and Q cannot fully separate them.
6. Technical exclusions were not MCAR: they track essay length and request
   congestion. The audited primary exclusions were not associated with ELL,
   and conservative bounds could not reverse the primary conditional mean
   direction — but the mechanism is real and disclosed.
7. **The real-data effect is predominantly location-based**, so conventional
   mean statistics also detect it (the mean-disparity baseline rejects in
   every cell). The unique value of the omnibus G² is demonstrated in the
   controlled variance-only and shape-only simulations, not in the PERSUADE
   result itself.

## Space allocation for the two-page Junior Spotlight submission

**MUST INCLUDE**
- The audit method in one paragraph + the exactness argument (conditional
  permutation within (prompt, human-score) strata).
- Synthetic validation headline: correct size; detects variance-only and
  shape-only departures that mean statistics miss (one compact row of
  numbers or a small table).
- Primary confirmatory result (GPT plain) with N, G², p, Δ.
- Three-judge replication + Holm family in one table row each.
- Paired ignore-demographics finding: the debiasing instruction did not
  mitigate and slightly worsened the conditional gap (estimate + interval).
  This is the single most decision-relevant new fact.
- One-sentence robustness line: richer human-quality and length adjustment
  attenuates the gap by at most ~11% and never below p = 0.001.
- Interpretation-limit sentence covering C3–C5 and C7.

**NICE IF SPACE**
- Judge-vs-human alignment one-liner (QWK/Spearman range + GPT compression)
  to preempt "are these evaluators functioning at all?".
- Exclusion-audit one-liner (length/congestion-driven, ELL-neutral, bounds
  cannot flip the sign).
- Cumulative shift profile (the dependence concentrates at P(S ≥ 4)).

**SUPPLEMENT / REPO ONLY**
- Full feasibility tables, stratum diagnostics, confusion matrices,
  transition matrices, negative control, power curves, Q construction
  details, bootstrap details, deviations D1/D2, all JSON artifacts.

The two-page story: a validated conditional-independence audit; a
preregistered, replicated residual ELL dependence across three commercial
judges; and the headline practical finding that a natural prompt-level
mitigation did not remove it — with honest limits on what "residual
dependence" does and does not mean.
