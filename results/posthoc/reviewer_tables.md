# Post-hoc robustness tables (reviewer-facing)

**All quantities below are POST-HOC robustness / descriptive analyses** (frozen plan:
`docs/posthoc_robustness_plan.md`, committed before execution). None are confirmatory.

## Table R1 — richer-quality conditional robustness (plain-rubric cells)

Δ = stratum-size-weighted conditional ELL − non-ELL mean judge score over informative strata.
Z0 = (prompt, human score); Z1 = Z0 + human discourse-effectiveness tertile; Z2 = Z1 + length median-split.
Feasibility (manifest): Z1 retains 99.0% of ELL essays, 66 informative strata; Z2 retains 97.5%, 111 strata — both pass the pre-set gates (>=70% ELL, >=20 strata).

| Judge | Δ_Z0 | Δ_Z1 | Δ_Z2 | G² Z0 | G² Z1 | G² Z2 | MAE vs Y | Spearman vs Y |
|---|---|---|---|---|---|---|---|---|
| GPT-5.4-mini | -0.3202 | -0.3068 | -0.3063 | 420.86 (p=0.001) | 437.75 (p=0.001) | 480.19 (p=0.001) | 0.5869 | 0.6403 |
| Claude Haiku 4.5 | -0.5982 | -0.5743 | -0.5509 | 691.58 (p=0.001) | 725.06 (p=0.001) | 768.13 (p=0.001) | 0.6247 | 0.6173 |
| Gemini 3.7 Flash | -0.444 | -0.4303 | -0.3958 | 500.95 (p=0.001) | 526.63 (p=0.001) | 605.27 (p=0.001) | 0.4676 | 0.782 |

Attenuation of |Δ| from Z0: GPT 4.2% (Z1) / 4.3% (Z2); Haiku 4.0% / 7.9%; Gemini 3.1% / 10.9%.
Permutation p-values are Monte Carlo (B = 999, +1 rule); 0.001 is the smallest attainable value.

## Table R2 — paired plain vs ignore-demographics (GPT-5.4-mini, post-hoc)

| Paired N (ELL) | Δ_plain | Δ_ignore | Attenuation (Δ_ignore − Δ_plain) | 95% interval | post-hoc p |
|---|---|---|---|---|---|
| 10353 (942) | -0.3138 | -0.3707 | -0.0568 | [-0.0928, -0.0144] | 0.022 |

Interpretation per the frozen rule (estimate + interval): the instruction did not mitigate the
conditional ELL gap; the estimate and its interval indicate a small **worsening** (the interval
excludes zero on the negative side). The instruction raised scores overall (mean D = 0.1585; non-ELL 0.1618, ELL 0.1253); 82.4% of paired scores were unchanged.

This is a new post-hoc test outside the preregistered Holm family; no equivalence claim is made from p alone.
