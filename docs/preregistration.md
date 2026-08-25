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
- `P` — writing prompt (14 prompts with ELL coding)

This is an **observational conditional-dependence null**. `Y` is an observed
human rating serving as a proxy for the intended writing construct, not
ground truth. See §18 for what a rejection does and does not mean.

## 3. Dataset and inclusion criteria

PERSUADE 2.0 (Crossley et al. 2024, *Assessing Writing* 61), canonical
distribution via https://github.com/scrosseye/persuade_corpus_2.0, CC
BY-NC-SA 4.0, SHA-256 checksums in `data/persuade/README.md`. Deduplicated to
25,996 essays keyed by `essay_id_comp`.

Included: essays with non-missing `prompt_name`, `holistic_essay_score`, and
`ell_status`, belonging to a **usable** `(prompt, human_score)` stratum — one
with at least two essays and both ELL categories observed. Population:
**23,334 essays, 61 usable strata, 2,235 ELL**. Both raw missing encodings of
`ell_status` (`''` and `' '`) are missing data (§15). The prompt "Phones and
driving" has no ELL coding and is therefore absent by the inclusion rule, not
by choice.

## 4. Sampling procedure

Primary sample of **n = 10,000** essays (§10), drawn before any scoring and
without reference to any future judge output:

1. proportional allocation across the 61 usable strata by the
   largest-remainder method;
2. simple random sampling without replacement within each stratum, with a
   position-addressed per-stratum seed
   (`SeedSequence(entropy=20260825, spawn_key=(stratum_index,))`), strata
   ordered lexicographically.

The procedure is deterministic given the frozen seed and **never consults
ELL status for individual selection** (the attribute enters only the
population-level usable-stratum definition fixed at feasibility). The test
suite verifies that permuting the ELL column leaves the selected IDs
unchanged. ELL counts in the sample are therefore random with expectation
matching the population share (~9.6%, ≈ 958 expected); we do **not**
oversample ELL. (Oversampling would change the estimand: the permutation
test would still be valid for the sampled conditional law, but descriptive
quantities would weight ELL essays differently from the corpus population.
If detecting weaker effects ever justifies it, that is a new design, not a
tweak.)

The manifest (`essay_id_comp`, `prompt_name`, `task` only — no attribute, no
human score) is written before scoring and is immutable thereafter.

## 5. Judge and rubric

The rubric is the corpus's own holistic rating form (SAT-based, 1–6), taken
verbatim from the canonical PDFs (`sat_rubric_only_indy.pdf`,
`sat_rubric_only_source_based.pdf`) including their typographical quirks, one
variant per task type. Frozen prompt templates: [`prompts/`](../prompts/).

The judge receives: task-appropriate rubric, the assignment text shown to the
student, source-text **titles** for text-dependent prompts, and the essay.
The canonical corpus does not distribute the source passages (third-party
copyrighted articles); the prompt states this explicitly. Consequence: the
judge scores text-dependent essays without the sources the human raters had.
This affects what the judge's score measures, not the validity of the test,
and `P` is in the conditioning set, so task- or prompt-specific judge
behaviour cannot by itself induce dependence within strata.

The judge NEVER receives: ELL status, any demographic field, the human
holistic score, or any corpus metadata beyond the materials above. Enforced
structurally (the prompt builder cannot accept such arguments) and by tests.

Output: exactly `SCORE: <integer 1–6>`; no chain-of-thought is requested or
stored; temperature 0 (plus a fixed seed parameter where offered). Providers
do not guarantee bitwise determinism; the analysis does not assume it.

Judges (§7 of the design discussion): **primary gpt-5-mini (OpenAI)**;
**secondary claude-haiku-4-5 (Anthropic) and gemini-2.5-flash (Google)**.
Exact snapshot IDs, availability, and pricing must be verified and recorded
in `config/preregistered.json` before the first call; if the primary judge
is unavailable, the substitution will be chosen before scoring and recorded
as a pre-scoring amendment.

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

**n = 10,000** (of 23,334). Rationale recorded at freeze time from the
planning simulations (observed strata, observed ELL imbalance, native
6-category scores; see `persuade_feasibility.md` for the planning model and
its assumptions): rejection rates at alpha = 0.05 were
| n | Type I (pi=0) | weak (pi=0.05) | moderate (pi=0.10) | strong (pi=0.20) |
|---|---|---|---|---|
| 4,000 | 0.036 | 0.172 | 0.374 | 0.884 |
| 8,000 | 0.042 | 0.300 | 0.752 | 0.990 |
| **10,000** | 0.064 | 0.348 | **0.840** | 1.000 |
| 12,000 | 0.032 | 0.444 | 0.914 | 1.000 |
| 23,334 | 0.052 | 0.830 | 1.000 | 1.000 |

(500 replicates/cell; Monte Carlo SE ≈ 0.010 near 0.05, ≈ 0.018 near 0.8;
the two null-cell departures from 0.05 are within that noise.)
Planning power at n = 10,000 is 0.840 for the moderate planning alternative
(0.1-point conditional mean shift) while remaining feasible in calls
(§ inference volume) before the deadline; n = 4,000 would be powered only
for strong effects, and the weak alternative is out of reach of any sample
smaller than approximately the full usable corpus. These planning
alternatives are not universal effect-size thresholds. The frozen seed
makes the sample deterministic; the realized draw (verified in the dry run,
before any scoring) contains 943 ELL essays and 56 informative strata — both
above the §19 failure thresholds.

Inference volume at n = 10,000: 10,000 calls for the primary test; 40,000
calls for the full confirmatory program (primary judge x 2 conditions +
2 secondary judges x plain). Mean essay ≈ 418 words; template ≈ 680–760
words; ≈ 1,500 input tokens/call ≈ 60M input tokens for the full program,
~10 output tokens/call.

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
20260825; permutation seed 427183 with per-test spawn slots; negative-control
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
- **Power failure**: realized informative strata < 45 or realized ELL < 700
  in the analysed sample → report as underpowered relative to plan; do not
  silently re-draw a larger sample after seeing results.
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
