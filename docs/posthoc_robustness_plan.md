# Post-hoc robustness analysis plan (FROZEN before execution)

**Status:** POST-HOC. The preregistered confirmatory program is complete and
its results are known (all four cells reject; Holm family complete). Nothing
in this document is confirmatory, and nothing below may be promoted to
confirmatory status. This plan exists so that, *within* the post-hoc stage,
analysis choices are fixed before their results are seen. Once this file is
committed, the analyses below are run exactly as written; results do not feed
back into binning rules, statistics, or exclusion rules.

Frozen: 2026-08-25, before any statistic in this plan was computed from judge
scores.

## 1. Frozen inputs (reused, never modified)

Confirmatory state at freeze time: HEAD =
`6f4c6358811d348c7084eae791ae93acdc3a25a0`
("Secondary confirmatory cell 2 frozen + Holm family complete").

Key upstream commits:

| commit | content |
|---|---|
| `74b9332ed2c709b609d21de51b1dbb5e2cd0be3a` | Stage A freeze: sample manifest |
| `d00044cbf52ff8e62e2bf3e8acb1cccf9119411f` | primary scoring frozen |
| `18524ccab51580e4dc97e043aa68ba057a8d6c06` | Stage E primary analysis |
| `9f57202ed2c09a84128631f49424db9e01363a97` | Haiku plain cell frozen |
| `20f35106335027fba182e57243b4e92018c31030` | GPT ignore-demographics cell frozen |
| `6f4c6358811d348c7084eae791ae93acdc3a25a0` | Gemini plain cell frozen + Holm family |

Frozen judge score files (SHA-256 from each cell's `FROZEN.json`, re-verified
before use):

| cell | file | sha256 |
|---|---|---|
| GPT-5.4-mini plain | `data/scoring/primary/scores__gpt-5.4-mini-2026-03-17__plain.jsonl` | `5fc3370745f37e15bc14be97b91dacbf144c12a6507cbc2ac34fbf87f6103506` |
| Haiku 4.5 plain | `data/scoring/secondary_haiku_plain/scores__claude-haiku-4-5-20251001__plain.jsonl` | `1f9c2d42eba4ecae40dbeef7fe94655c980cf98c33e767bf3f0bb8bac141a516` |
| Gemini 3.7 Flash plain | `data/scoring/secondary_gemini_plain/scores__gemini-3.7-flash__plain.jsonl` | `dd37958ad753f3b75fde4fc26c5e1194e4898ac8925010dc0892f36fd408c738` |
| GPT-5.4-mini ignore-demographics | `data/scoring/secondary_gpt_ignore/scores__gpt-5.4-mini-2026-03-17__ignore_demographics.jsonl` | `0db40aa3d102ed531594d01433b3d9b547f65b3f93d80459d586eda20738f678` |

Other frozen inputs:

- `data/scoring/primary_sample_manifest.csv` (n = 11,360; Independent task; 7
  prompts; 31 usable `(prompt, holistic score)` strata) — sha256
  `c226fcab56357ec27ef8ae67e75db67f8e655b871357d7440fa1e5461fbb713d`.
- `data/persuade/persuade_essay_level.csv` — sha256
  `b45aa58f7c4b4d9018511515cd1cf1dd409299ea093329272a05571f8203be8f`.
- Raw corpus CSVs `persuade_train.csv` / `persuade_corpus_2.0_test.csv`
  (source SHA-256 recorded in `data/persuade/README.md`), used ONLY to read
  the human discourse-effectiveness annotations and `essay_word_count`.

Hard rules inherited from the user brief: **no new LLM API calls; no rerun,
alteration, replacement, or exclusion of existing judge scores; no new
demographic attributes; no per-prompt significance tests; no source-based
PERSUADE prompts; the preregistered primary and secondary results are not
touched.**

## 2. New variables

### 2.1 Human quality index Q (Stage 1)

Source: the human `discourse_effectiveness` annotation attached to each
annotated discourse element in the canonical corpus CSVs. Verified semantics
(inspected 2026-08-25 on the local canonical files): the field takes exactly
three ordinal levels — `Ineffective`, `Adequate`, `Effective` — and is missing
(NaN) exactly on `discourse_type == "Unannotated"` spans, which are
non-element filler text between annotated discourse elements. This is the
corpus's argumentation-effectiveness scale (see
`data/persuade/rubrics/argumentation_effectiveness_rubric.pdf`; the same
three-level scale was used in the Feedback Prize effectiveness task).

Ordinal mapping (fixed a priori, the standard integer coding of the ordinal
scale, equal spacing asserted as a working simplification and stated as such):

    Ineffective = 0, Adequate = 1, Effective = 2

Essay-level index:

    Q(essay) = mean of mapped effectiveness over the essay's annotated
               discourse elements (Unannotated/NaN rows excluded)

Construction details, all A-free and S-free:

- Rows are read from `persuade_train.csv` + `persuade_corpus_2.0_test.csv`,
  restricted to the 11,360 manifest essays, with exact duplicate
  `(essay_id_comp, discourse_id)` rows dropped as a safeguard (none expected).
- No demographic column and no judge output is read at this step.
- Pre-verified coverage (schema check only, no ELL/judge join): 100% of the
  11,360 manifest essays have >= 1 usable effectiveness annotation, so **no
  essay is dropped for missing Q**. If that were ever violated the rule is:
  essays without usable annotations are excluded from Z1/Z2 and counted.
- Output `results/posthoc/quality_index.csv` with columns
  `essay_id_comp, n_effectiveness_elements, quality_index`; SHA-256 recorded
  and the file committed BEFORE any join with ELL status or judge scores.

Descriptives to report (A-free, S-free except the human holistic score Y,
which is not a judge output): number of annotated elements per essay;
fraction of essays with usable annotations; distribution of Q; relationship
between Q and Y (Spearman rho, mean Q per Y level).

### 2.2 Human-quality bin (Stage 2)

Within each of the 31 original Z0 = `(prompt, Y)` strata, compute the
empirical tertile cutpoints of Q (`numpy.quantile`, default linear
interpolation, probabilities 1/3 and 2/3) over the manifest essays in that
stratum, and assign:

    bin 0 if Q <= q(1/3);  bin 1 if q(1/3) < Q <= q(2/3);  bin 2 if Q > q(2/3)

Identical Q values always land in the same bin (value-based cut, no
rank-splitting of ties). Ties may make bins uneven or empty; that is accepted
and reported, never repaired. The number of bins (3) and the within-stratum
construction are fixed now and will not be changed after seeing feasibility
or robustness results.

### 2.3 Length bin (Stage 4)

Length variable: `essay_word_count` from the corpus metadata (A-free,
S-free). Within each Z1 stratum, split at the within-stratum median
(`numpy.median`):

    bin 0 if word_count <= median;  bin 1 if word_count > median

Two bins, fixed a priori. Same tie rule: equal values share a bin.

## 3. Conditioning sets

- Z0 = `(prompt, Y)` — the original confirmatory conditioning (31 strata).
- Z1 = `(prompt, Y, quality bin)` — Stage 2.
- Z2 = `(prompt, Y, quality bin, length bin)` — Stage 4, nested in Z1.

No pooling of sparse strata at any level. Degenerate strata (single essay or
single ELL category) contribute nothing to the statistic, exactly as in the
confirmatory analysis.

## 4. Feasibility gates (evaluated on the manifest + ELL, BEFORE joining judge scores)

For each of Z1 and Z2, report: total strata; informative strata (>= 2 essays
and both ELL categories); effective N and ELL N inside informative strata;
degenerate strata (size 1); thin strata (size < 10); fraction of the
manifest's 1,039 ELL essays retained in informative strata; min/median/max
stratum size.

A conditioning set is inferentially usable ONLY if, on the manifest:

- >= 70% of the 1,039 ELL observations are retained in informative strata, AND
- >= 20 informative strata exist.

If a gate fails, the corresponding permutation test is NOT run; the failure
is preserved as a feasibility finding and the richer variables are used only
descriptively. Bins are not loosened after seeing feasibility.

## 5. Statistics

### 5.1 Richer-conditioning robustness tests (Stage 3, and Stage 4 if Z2 passes)

For each plain-rubric judge cell (GPT-5.4-mini, Haiku 4.5, Gemini 3.7 Flash)
and each usable conditioning set, run the identical frozen framework:
`conditional_g2` with within-stratum Monte Carlo permutation, B = 999,
p = (1 + #{T_b >= T_obs}) / (B + 1), using
`offcriterion.permutation.permutation_test` unchanged. The ignore-
demographics cell is NOT included here.

Seeds: `permutation_seed = 427183` (unchanged) with NEW reserved spawn keys
so no confirmatory stream is reused: Z1 tests (10, j) and Z2 tests (11, j)
for j = 0 (GPT), 1 (Haiku), 2 (Gemini); Stage 6 permutation (12, 0); Stage 6
bootstrap (12, 1).

Per judge and conditioning set, report: N analysed; ELL N; informative
strata; observed G^2; Monte Carlo p; conditional mean difference Δ
(stratum-size-weighted ELL-minus-non-ELL mean over informative strata, the
frozen `_weighted_diagnostics` definition); cumulative ordinal shift profile
P(S >= k), k = 2..6, same weighting.

Attenuation, per judge:

    attenuation(Z1) = Δ_Z1 − Δ_Z0,  attenuation(Z2) = Δ_Z2 − Δ_Z0

with Δ_Z0 the ORIGINAL frozen confirmatory conditional mean difference for
that judge. Because Z1/Z2 samples can differ from the Z0 sample only through
informative-stratum membership (Q coverage is 100%), a composition-matched
check Δ_Z0* — Z0 weighting recomputed on exactly the Z1 (resp. Z2) analysis
sample — is also reported alongside. Report absolute change and percentage
attenuation in magnitude, |Δ| basis Δ_Z0.

These p-values are post-hoc robustness quantities. They carry no
confirmatory status regardless of magnitude.

### 5.2 Judge-vs-human alignment (Stage 5, descriptive only)

For each of the four cells, against Y on the 1–6 scale: exact agreement;
within-1 agreement; MAE; RMSE; Spearman rho; Pearson r; quadratic weighted
kappa (standard 6x6 quadratic weights); full 6x6 Y-by-S confusion matrix;
judge and human marginal distributions; compression metrics — Shannon
entropy (bits) of the judge marginal, effective number of categories 2^H,
fraction in the two most common categories, min and max category actually
awarded.

Two versions: (A) each cell on all of its own valid observations; (B) the
complete-case intersection of essays valid in ALL FOUR cells — version B is
the basis for any direct cross-judge comparison. No hypothesis tests; no
"best judge" claim.

### 5.3 Paired plain vs ignore-demographics (Stage 6, post-hoc)

Sample: essays with a valid GPT-5.4-mini score under BOTH conditions.
Per essay D_i = S_ignore,i − S_plain,i. Strata: original Z0.

Estimand: stratum-size-weighted difference over informative Z0 strata

    T = Σ_g w_g [ mean(D | ELL, g) − mean(D | non-ELL, g) ] / Σ_g w_g
      = Δ_ignore − Δ_plain   (both gaps computed on the paired sample)

Positive T = the instruction moved ELL essays up relative to non-ELL essays
(attenuation of the negative gap).

Test: within-stratum permutation of A holding (D, Z) fixed; B = 999; the
same +1 rule; TWO-SIDED via |T|: p = (1 + #{|T_b| >= |T|}) / (B + 1).
This is a new post-hoc test outside the Holm family.

Uncertainty: stratified bootstrap — within each informative Z0 stratum,
resample essays with replacement holding stratum sizes fixed; strata that
lose an ELL category in a draw drop out of that draw's weighted mean; 2,000
replicates; percentile 95% interval (2.5, 97.5). Seed slot (12, 1).

Also report: paired N and paired ELL N; Δ_plain and Δ_ignore on the paired
sample; the 6x6 plain-to-ignore score transition matrix, overall and split
by ELL status (descriptive).

Interpretation rule fixed now: conclusions are drawn from the estimate and
interval — "evidence of mitigation", "evidence of worsening", or
"insufficient precision to establish either". No equivalence claim from
p > .05; no equivalence margin invented after the fact.

## 6. Planned outputs

Tables (all under `results/posthoc/`, all labeled POST-HOC):

1. `quality_index.csv` (+ sha256, frozen pre-join) and Q descriptives.
2. Z1/Z2 feasibility table (Section 4 quantities).
3. Per-judge Z0/Z1(/Z2) robustness table: N, ELL N, informative strata, G^2,
   p, Δ, cumulative shift profile.
4. Compact attenuation table: Δ_Z0, Δ_Z1, Δ_Z2, absolute and % attenuation.
5. Stage 5 alignment metrics, versions A and B, plus four confusion matrices.
6. Stage 6 paired summary + transition matrices.
7. Reviewer-facing combined table (Stage 7): rows = three plain judges;
   columns = Δ_Z0, Δ_Z1, Δ_Z2 (if feasible), original G^2 + p, richer G^2 +
   p, MAE vs Y, Spearman vs Y. Plus a one-row paired-prompting table:
   paired N, Δ_plain, Δ_ignore, attenuation, 95% interval, post-hoc p.

Plots: none are generated at this stage; confusion matrices and shift
profiles are reported as tables. Any figures for the paper are typesetting
of these frozen numbers, not new analysis.

Documents: `docs/junior_spotlight_evidence.md` (evidence hierarchy,
Stage 8) and the Stage 9 space-allocation recommendation.

## 7. Interpretation boundaries (fixed now)

1. Nothing here is confirmatory; all of it is labeled post-hoc robustness /
   descriptive.
2. The human holistic score is a benchmark reference, not ground truth; the
   discourse-effectiveness annotations are likewise imperfect human proxies.
3. Attenuation quantities are sensitivity analysis, NOT causal mediation;
   persistence of residual dependence does not establish demographic
   discrimination or causal use of ELL status; ELL-correlated linguistic
   features may be construct-relevant under a writing rubric.
4. Stage 5 metrics characterize construct alignment; they do not rank
   judges inferentially.
5. Stage 6 conclusions follow the estimate-and-interval rule in 5.3.
6. A feasibility-gate failure is itself a finding ("exact adjustment at that
   resolution is too sparse") and does not license rule changes.
