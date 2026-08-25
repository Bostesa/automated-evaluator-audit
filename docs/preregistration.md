# Preregistration: OffCriterion on PERSUADE 2.0

Frozen 2026-08-25, **before any LLM judge scoring**. Machine-readable
parameters: [`config/preregistered.json`](../config/preregistered.json).
Statistical assumptions and their status: [`assumptions.md`](assumptions.md).
Feasibility evidence: [`persuade_feasibility.md`](persuade_feasibility.md).

## 1. Research question

Does an LLM judge's holistic essay score retain information about the
writer's English-language-learner (ELL) status beyond what the observed human
holistic score and the writing prompt explain?

## 2. Primary hypothesis

```
H0 :  S  _||_  A  |  Y, P
```

- `S` — LLM judge holistic score (native 1–6 rubric scale; not yet collected)
- `A` — writer ELL status (`Yes` / `No`)
- `Y` — PERSUADE human holistic score (1–6)
- `P` — **independent-writing** prompt (7 prompts with ELL coding; §21)

This is an **observational conditional-dependence null**. `Y` is an observed
human rating serving as a proxy for the intended writing construct, not
ground truth. See §18 for what a rejection does and does not mean.

## 3. Dataset and inclusion criteria

PERSUADE 2.0 (Crossley et al. 2024, *Assessing Writing* 61), canonical
distribution via https://github.com/scrosseye/persuade_corpus_2.0, CC
BY-NC-SA 4.0, SHA-256 checksums in `data/persuade/README.md`. Deduplicated to
25,996 essays keyed by `essay_id_comp`.

Included: essays with `task == "Independent"` and non-missing
`prompt_name`, `holistic_essay_score`, and `ell_status`, belonging to a
**usable** `(prompt, human_score)` stratum — one with at least two essays and
both ELL categories observed. Population: **11,360 essays, 31 usable strata,
1,039 ELL, 7 prompts** (`results/persuade_feasibility_independent/`). Both
raw missing encodings of `ell_status` (`''` and `' '`) are missing data
(§15). The prompt "Phones and driving" has no ELL coding and is therefore
absent by the inclusion rule, not by choice.

**Why Independent-task only (v2 revision, §21):** the canonical corpus does
not distribute the source passages for Text-dependent prompts (only their
titles; the passages are third-party copyrighted articles). The human
holistic rubric for source-based writing explicitly evaluates evidence taken
from the source text, so a judge without the passages cannot measure the
construct the human raters measured — a construct mismatch that conditioning
on prompt does not repair. Text-dependent prompts may appear only in clearly
labelled exploratory analyses, with the mismatch stated. No passages are
reconstructed, summarised, substituted, or scraped.

## 4. Sampling procedure

The primary sample is a **census of the full usable Independent-task
pool: n = 11,360** (§10), fixed before any scoring and without reference to
any future judge output. The selection code path (largest-remainder
allocation + within-stratum SRS, frozen seed 20260901) reduces to a census
at the full pool size, so the draw is deterministic and seed-independent —
verified by test. There is no sampling variance, no ELL oversampling (ELL
count is the population's 1,039, 9.1%), and the estimand is the usable-pool
conditional law itself.

The manifest (`essay_id_comp`, `prompt_name`, `task` only — no attribute, no
human score) is written before scoring and is immutable thereafter.

## 5. Judge and rubric

The rubric is the corpus's own holistic rating form for independent
writing (SAT-based, 1–6), taken verbatim from the canonical
`sat_rubric_only_indy.pdf` including its typographical quirks. Frozen prompt
template: [`prompts/judge_prompt_independent.txt`](../prompts/judge_prompt_independent.txt).
(The source-based template remains in the repository solely for possible
exploratory use, per §3.)

The judge receives: the independent-writing rubric, the assignment text
shown to the student, and the essay — nothing else.

The judge NEVER receives: ELL status, any demographic field, the human
holistic score, or any corpus metadata beyond the materials above. Enforced
structurally (the prompt builder cannot accept such arguments) and by tests.

Output: exactly `SCORE: <integer 1–6>`; no chain-of-thought is requested or
stored; temperature 0 (plus a fixed seed parameter where offered). Providers
do not guarantee bitwise determinism; the analysis does not assume it.

Judges, verified 2026-08-25 against official provider documentation
(details and rejected alternatives in `config/preregistered.json`):

- **Primary: `gpt-5.4-mini-2026-03-17`** (OpenAI; pinned snapshot; $0.75/$4.50
  per MTok; structured outputs; reasoning effort `none` by default).
  `gpt-5.6-luna` is newer and cheaper but has **no pinned snapshot** — a
  mutable alias is incompatible with a frozen, replicable design;
  `gpt-5-mini` is pinned but a year old.
- **Secondary: `claude-haiku-4-5-20251001`** (Anthropic; pinned; $1/$5 per
  MTok) and **`gemini-3.7-flash`** (Google; stable version ID; $0.75/$3.75
  per MTok promotional through 2026-12-31; thinking tokens bill as output, so
  the thinking-budget control must be verified before scoring).

If a listed judge is unavailable at scoring time, the substitution is chosen
before any call and recorded as a pre-scoring amendment (§20).

## 6. Primary condition

The **plain rubric** condition: the frozen template with no demographic
instruction. The `ignore_demographics` condition (one added paragraph,
otherwise byte-identical) is **secondary**, so the primary question does not
depend on prompt engineering.

## 7. Primary statistic

Conditional G² on the `(S, A, Z)` contingency table with
`Z = (prompt, human_score)` strata and the **native six score categories**
(category space fixed at 1..6 a priori; no quantile binning; empty categories
are harmless):

```
G^2 = 2 * sum_{z,s,a} n_zsa * log(n_zsa * n_z / (n_zs * n_za)) = 2n * I_hat(S; A | Z)
```

as implemented in `offcriterion.statistics.ConditionalG2` and validated in
the synthetic stage. It is omnibus with respect to the six-category law.

## 8. Permutation procedure

The existing within-stratum permutation test
(`offcriterion.permutation.permutation_test`): `A` permuted only within exact
`(prompt, human_score)` strata, `S` and `Z` fixed, stratum attribute counts
preserved. Strata with one observed ELL category contribute no permutation
information; they are retained in counts and contribute nothing to the
statistic. **No pooling of sparse strata.**

Assumptions required for finite-sample validity of this random-permutation
inference (full statement and failure modes in `assumptions.md`):

- **A1** units are independent draws (or at least exchangeable within
  strata): no repeated writers, duplicates, or dependent scoring calls
  treated as independent units. PERSUADE has no writer ID; A1 is argued from
  the corpus documentation and the absence of duplicate texts, and is the
  assumption most at risk.
- **A2** conditioning is on the exact observed `(Y, P)`; the guarantee is
  relative to this conditioning set. `Y` is a proxy, so this null is the
  proxy-conditional null (§18).
- **A3** every preprocessing step is A-free (enforced structurally).
- **A4** permutations are drawn i.i.d. uniform within strata; with `B`
  random draws and the `+1` construction the test is finite-sample valid for
  any `B` (no exhaustive enumeration is implied).

## 9. Alpha and Monte Carlo settings

`alpha = 0.05`, `B = 999`, `p = (1 + #{T_b >= T_obs}) / (B + 1)`; minimum
attainable p = 0.001, sufficient for the Holm family of 3 (§11). Permutation
RNG: `SeedSequence(entropy=427183, spawn_key=slot)` with slots frozen in the
config.

## 10. Primary sample size

**n = 11,360 — the full usable Independent-task pool (census).** Planning
simulations on the exact independent-only stratum structure (same planning
model as before: observed strata and ELL labels, judge
`S = clamp(Y + e, 1, 6)` with `P(e = −1, 0, +1) = (0.2, 0.6, 0.2)`, ELL
downshift probability π; 500 replicates/cell, B = 999, α = 0.05;
`results/persuade_feasibility_independent/power_planning.csv`):

| n | Type I (π=0) | weak (π=0.05) | moderate (π=0.10) | strong (π=0.20) |
|---|---|---|---|---|
| 4,000 | 0.062 | 0.218 | 0.540 | 0.948 |
| 6,000 | 0.044 | 0.306 | 0.726 | 0.992 |
| 8,000 | 0.046 | 0.390 | 0.892 | 1.000 |
| 10,000 | 0.048 | 0.526 | 0.946 | 1.000 |
| **11,360** | 0.044 | **0.608** | **0.970** | **1.000** |

(Monte Carlo SE ≈ 0.010 near 0.05, ≈ 0.02 near 0.6–0.9; null cells are all
within noise of 0.05.) The census costs only 14% more calls than n = 10,000,
buys the best achievable power under this design — 0.970 moderate, 0.608
weak — and eliminates sampling variance entirely. These planning
alternatives are a specific synthetic mean-shift model, not universal
detectable-effect thresholds; in particular, weak dependence (π = 0.05) has
only ~0.61 power even at the census, and a null result must not be read as
evidence against it.

The frozen census (verified in the dry run, before any scoring): 11,360
essays, **1,039 ELL**, **31 informative strata**, 7 prompts, human scores
1: 62 · 2: 1,932 · 3: 3,409 · 4: 3,597 · 5: 2,024 · 6: 336.

Inference volume (mean essay 434.5 words + 736 words prompt overhead at
1.3–1.4 tokens/word ≈ 1,520–1,640 input tokens/call; ~10 output
tokens/call): 11,360 calls and ≈ 17.3–18.6M input tokens per
judge-condition; 45,440 calls for the full confirmatory program. Estimated
costs from verified official prices: primary ≈ **$13.0–14.5**; complete
confirmatory program ≈ **$56–63** (gpt-5.4-mini both conditions
$26.0–29.0; claude-haiku-4-5 $17.4–19.2; gemini-3.7-flash $13.0–14.5 plus
thinking-token uncertainty pending the §5 verification).

## 11. Multiplicity plan

- **Primary family (no correction): exactly one test** — primary judge,
  plain condition, ELL, conditional G², alpha = 0.05.
- **Secondary confirmatory family (Holm, m = 3, alpha = 0.05):**
  1. secondary judge 1, plain, ELL, G²;
  2. secondary judge 2, plain, ELL, G²;
  3. primary judge, ignore-demographics, ELL, G².
  Secondary-judge results are reported per judge with Holm-adjusted
  p-values; they are corroboration, and no judge may be promoted to
  "primary" after results are seen.
- **Everything else is exploratory**, reported uncorrected and clearly
  labelled, never as confirmatory evidence: other attributes (gender,
  race/ethnicity, economic disadvantage, disability), alternative statistics,
  task-type subgroups, asymptotic baselines, descriptive diagnostics.

## 12. Secondary analyses

On the same frozen scores: the two permutation-calibrated companion
statistics (stratified mean disparity; stratified regression LRT) evaluated
on the same permutation draws as G²; the marginal Welch t-test and the
asymptotic stratified F-test as clearly-labelled reference points that test
different or asymptotically-calibrated nulls; exploratory attribute analyses
(each attribute defines its own usable strata).

## 13. Controls

**Negative control (randomized labels).** One within-stratum random
relabelling of `A` (frozen seed 771029) run through the *entire* analysis
path as if it were the real attribute. What this adds beyond the permutation
test's own null distribution: the permutation machinery guarantees
calibration only for the `(S, A, Z)` arrays actually handed to it. The
negative control validates everything upstream of that handoff on the real
scored data — the ID joins, the exclusion bookkeeping, the stratum coding,
the score parsing — because with relabelled `A` the null holds *by
construction* regardless of judge behaviour, so a small p-value can only
come from a pipeline defect (misaligned join, exclusions correlated with
labels, leakage). It is not additional evidence of the mathematical validity
of the test itself. A single draw rejects with probability alpha under a
correct pipeline, so a rejection triggers the diagnostic sweep — 200
relabelling draws, p-values checked for approximate uniformity (exploratory,
no scoring cost) — rather than an automatic failure declaration.

**Positive control: DROPPED** for the Junior Spotlight version. HelpSteer2
correctness-conditioned-on-verbosity would require a second corpus, a second
scoring budget, and a second narrative in a two-page paper; the synthetic
validation stage already demonstrates power against known alternatives and
calibration under known nulls. Revisit for any longer version.

## 14. Exclusion rules

1. A judge response that does not match `SCORE: <1–6>` exactly (after
   whitespace stripping) is excluded and logged verbatim; never repaired,
   never re-prompted.
2. An API call failing after 3 retries of the identical request is excluded
   as technical failure and logged.
3. No other exclusions of any kind.

## 15. Missing-data handling

Complete-case on `(prompt, human score, ELL)`; both raw encodings `''` and
`' '` count as missing ELL; no imputation; no third ELL category is created.
Missingness is documented (5.0% overall; one whole prompt/provider) in
`persuade_feasibility.md`, and complete-case inclusion is applied before
sampling, so scored essays never lack analysis variables.

## 16. Random seeds

All frozen before scoring, in `config/preregistered.json`: sampling seed
20260901 (vestigial under the census — the draw is seed-independent, verified
by test); permutation seed 427183 with per-test spawn slots; negative-control
label seed 771029. Every analysis component takes an explicit seeded
generator; nothing uses global RNG state.

## 17. Planned descriptive diagnostics

Fixed now so the explanatory decomposition cannot be chosen after seeing the
results. All are stratum-size-weighted contrasts between ELL and non-ELL
within informative strata, computed by `pipeline.analysis` alongside the
test:

1. weighted conditional mean difference of `S` (rubric points);
2. weighted conditional variance difference;
3. weighted cumulative shifts `P(S >= k | ELL) − P(S >= k | non-ELL)` for
   k = 2..6 (the ordinal shift profile);
4. the score distribution of `S` by attribute (counts, 1..6);
5. (exploratory) per-category contributions to G² and conditional moments
   via `offcriterion.diagnostics`.

Together these say whether a rejection is primarily a location shift, a
dispersion difference, or a tail/shape effect. They are descriptive, not
tests.

## 18. Interpretation boundaries

A rejection is evidence of **residual conditional dependence** between the
judge score and ELL status given the human score and prompt. It is NOT
evidence that the judge causally used ELL status; NOT evidence of
discrimination; NOT a claim that the human score is ground truth; NOT a
claim that the dependence is harmful or unjustified. Because `Y` is a proxy
for the construct, residual dependence can reflect construct-relevant signal
the human score misses, human-rater bias, or judge sensitivity to
ELL-correlated features irrelevant to the construct; the test does not
distinguish these. A non-rejection is not evidence of conditional
independence, especially against alternatives weaker than the planning
alternatives at the chosen n.

## 19. Falsification / failure criteria

Declared in advance:

- **Pipeline failure**: negative-control sweep (200 draws) departing clearly
  from uniformity (Kolmogorov–Smirnov p < 0.01, exploratory diagnostic) →
  find and fix the defect, document, and re-run analysis from frozen raw
  outputs; if the defect required re-scoring, the experiment restarts and
  says so.
- **Procedure failure**: > 5% unparseable responses from the primary judge →
  the primary result is reported with that caveat prominently; the judge is
  not swapped post hoc.
- **Power failure**: the census fixes the scored set (1,039 ELL, 31
  informative strata), so these thresholds guard post-exclusion attrition
  only: analysed ELL < 900 or informative strata < 28 after exclusions →
  report as underpowered relative to plan; do not silently re-score.
- The primary claim of the paper must survive the primary test alone; if
  p > alpha, the paper reports a null result with the power caveats of §10.

## 20. Deviations policy

Any departure from this document after any judge output has been observed
will be reported explicitly as a **post-preregistration deviation**, with
its trigger and its consequence for interpretation, in the paper and in this
repository. Amendments made before the first judge call (e.g. a verified
snapshot ID, or judge substitution for availability) are recorded in
`config/preregistered.json` and dated; they are pre-scoring amendments, not
deviations.

## 21. Revision log

- **v1 (2026-08-25).** Initial freeze: all 14 ELL-coded prompts, n = 10,000
  proportional stratified sample, primary judge gpt-5-mini (unverified).
- **v2 (2026-08-25, pre-data; no judge output of any kind has been
  observed).** (a) Primary restricted to Independent-task prompts: the
  corpus lacks the source passages for Text-dependent prompts, and the
  source-based human rubric explicitly evaluates evidence taken from the
  source text, so a judge without the passages measures a different
  construct than the human raters — a mismatch that conditioning on prompt
  does not repair. Text-dependent prompts are exploratory only. (b) Sample
  becomes a census of the usable independent pool (n = 11,360). (c) Judges
  verified against official documentation and pinned:
  gpt-5.4-mini-2026-03-17 primary (gpt-5.6-luna rejected for lacking a
  pinned snapshot), claude-haiku-4-5-20251001 and gemini-3.7-flash
  secondary. (d) Data thresholds restated for a census (§19). This is a
  legitimate pre-data design revision under the §20 policy.
